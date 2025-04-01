from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime
import pytz
import secrets
from dotenv import load_dotenv
from .graph import build_graph
import atexit

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Flask app initialization
app = Flask(__name__)
# Use a secure random key for sessions
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Compile LangGraph once at startup
try:
    compiled_graph = build_graph()
except Exception as e:
    logging.exception("Critical error compiling LangGraph.")
    compiled_graph = None

@app.route('/', methods=['GET', 'POST'])
def index():
    # Add extensive logging for debugging form submissions
    if request.method == 'POST':
        logging.info(f"POST request received at index with form data: {request.form}")
        
        # Handle configuration setup
        if 'setup' in request.form:
            tavily_key = request.form.get('tavily_api_key', '').strip()
            gemini_key = request.form.get('gemini_api_key', '').strip()
            user_email = request.form.get('user_email', '').strip()
            
            logging.info(f"Configuration attempt with email: {user_email}")
            
            if not all([tavily_key, gemini_key, user_email]):
                flash('All configuration fields are required.', 'error')
                return redirect(url_for('index'))
                
            from .config import set_credentials
            set_credentials(
                tavily_key=tavily_key, 
                gemini_key=gemini_key, 
                user_email=user_email,
                sender_email=os.getenv('SENDER_EMAIL', 'default@example.com'),
                sender_password=os.getenv('SENDER_APP_PASSWORD', '0000')
            )
            session['user_email'] = user_email
            session['configured'] = True
            flash('Configuration saved successfully.', 'success')
            return redirect(url_for('index'))
        
        # Handle newsletter topic submission
        elif 'topic' in request.form:
            topic = request.form.get('topic', '').strip()
            logging.info(f"Topic submitted: '{topic}'")
            
            if not topic:
                logging.warning("Empty topic detected")
                flash('Please enter a topic for your newsletter.', 'error')
                return redirect(url_for('index'))
                
            if not session.get('configured') or not session.get('user_email'):
                logging.warning("Attempted to start newsletter without configuration")
                flash('Please configure settings before generating a newsletter.', 'error')
                return redirect(url_for('index'))
                
            try:
                if compiled_graph:
                    # Generate and send the newsletter immediately
                    send_newsletter_now(compiled_graph, topic, session['user_email'])
                    flash(f'Newsletter for "{topic}" has been generated and sent to your email.', 'success')
                    session['last_topic'] = topic
                    logging.info(f"Successfully generated newsletter for topic: {topic}")
                else:
                    logging.error("Compiled graph is None, cannot generate newsletter")
                    flash('Error: Unable to generate newsletter.', 'error')
            except Exception as e:
                logging.exception(f"Error generating newsletter for topic '{topic}': {str(e)}")
                flash(f'Error generating newsletter: {str(e)}', 'error')
                
            return redirect(url_for('index'))
        
        else:
            logging.warning(f"POST request without recognized form action. Form data: {request.form}")
            flash('Unknown form submission. Please try again.', 'warning')
            return redirect(url_for('index'))

    # Prepare display data
    app_ready = bool(compiled_graph)
    is_configured = session.get('configured', False)
    last_topic = session.get('last_topic', None)
    user_email = session.get('user_email', '')

    return render_template(
        'index.html', 
        app_ready=app_ready,
        is_configured=is_configured,
        last_topic=last_topic,
        user_email=user_email
    )

# Function to generate and send newsletter immediately
def send_newsletter_now(graph, topic, user_email):
    """Generate and send a newsletter immediately."""
    from .graph import GraphState
    
    try:
        logging.info(f"--- Starting newsletter generation for topic: '{topic}' ---")
        
        # Create input state
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz).strftime("%d/%m/%Y at %H:%M")
        
        inputs = GraphState(
            topic=topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=user_email,
            timestamp=current_time
        )
        
        # Execute graph
        result = graph.invoke(inputs)
        
        # Handle result
        if result.get("error"):
            logging.error(f"Error during graph execution: {result['error']}")
            raise Exception(result['error'])
        else:
            logging.info("Newsletter generation and delivery completed successfully")
            return True
            
    except Exception as e:
        logging.error(f"Newsletter generation error: {str(e)}")
        raise

@app.route('/modify_config', methods=['GET', 'POST'])
def modify_config():
    """Allow users to modify their configuration"""
    if request.method == 'POST':
        tavily_key = request.form.get('tavily_api_key', '').strip()
        gemini_key = request.form.get('gemini_api_key', '').strip()
        user_email = request.form.get('user_email', '').strip()
        
        if not all([tavily_key, gemini_key, user_email]):
            flash('All configuration fields are required.', 'error')
            return redirect(url_for('modify_config'))
            
        from .config import set_credentials
        set_credentials(
            tavily_key=tavily_key, 
            gemini_key=gemini_key, 
            user_email=user_email,
            sender_email=os.getenv('SENDER_EMAIL', 'default@example.com'),
            sender_password=os.getenv('SENDER_APP_PASSWORD', '0000')
        )
        session['user_email'] = user_email
        session['configured'] = True
        flash('Configuration updated successfully.', 'success')
        return redirect(url_for('index'))
    
    # For GET requests, show the config form
    user_email = session.get('user_email', '')
    return render_template('modify_config.html', user_email=user_email)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    load_dotenv()
    from .config import load_credentials_from_env
    if os.getenv('TAVILY_API_KEY') and os.getenv('GEMINI_API_KEY'):
        load_credentials_from_env()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)