import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime
import pytz
from dotenv import load_dotenv
from . import config
from .graph import build_graph
# Change this import to use relative path
from ..scheduler import start_scheduling, stop_scheduling, get_active_state
import atexit

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Flask app initialization
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))



# Compile LangGraph once at startup
try:
    compiled_graph = build_graph()
except Exception as e:
    logging.exception("Critical error compiling LangGraph.")
    compiled_graph = None

# Ensure scheduler stops on app shutdown
atexit.register(stop_scheduling)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle configuration setup
        if 'setup' in request.form:
            tavily_key = request.form.get('tavily_api_key', '').strip()
            gemini_key = request.form.get('gemini_api_key', '').strip()
            user_email = request.form.get('user_email', '').strip()
            
            if not all([tavily_key, gemini_key, user_email]):
                flash('All configuration fields are required.', 'error')
                return redirect(url_for('index'))
                
            config.set_credentials(
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
            
            if not topic:
                flash('Please enter a topic for your newsletter.', 'error')
                return redirect(url_for('index'))
                
            if not session.get('configured') or not session.get('user_email'):
                flash('Please configure settings before starting a newsletter.', 'error')
                return redirect(url_for('index'))
                
            try:
                if compiled_graph:
                    stop_scheduling()
                    start_scheduling(compiled_graph, topic, session['user_email'], interval_hours=1)
                    flash(f'Monitoring started for "{topic}". First email sent, next ones hourly.', 'success')
                    session['active_topic'] = topic
                else:
                    flash('Error: Unable to start monitoring service.', 'error')
            except Exception as e:
                flash(f'Error starting monitoring: {str(e)}', 'error')
                logging.exception("Error starting scheduling")
                
            return redirect(url_for('index'))

    # Sync scheduler state with session
    scheduler_state = get_active_state()
    if scheduler_state['active'] and scheduler_state['topic']:
        session['active_topic'] = scheduler_state['topic']
    elif session.get('active_topic') and not scheduler_state['active']:
        session.pop('active_topic', None)

    # Prepare display data
    app_ready = bool(compiled_graph)
    is_configured = session.get('configured', False)
    active_topic = session.get('active_topic', None)
    user_email = session.get('user_email', '')

    # Format timing info
    last_execution = None
    next_execution = None
    time_remaining = None
    if scheduler_state['last_execution']:
        try:
            paris_tz = pytz.timezone('Europe/Paris')
            last_exec = datetime.fromisoformat(scheduler_state['last_execution'])
            last_execution = last_exec.astimezone(paris_tz).strftime("%H:%M:%S")
            if scheduler_state['next_execution']:
                next_exec = datetime.fromisoformat(scheduler_state['next_execution'])
                next_execution = next_exec.astimezone(paris_tz).strftime("%H:%M:%S")
                now = datetime.now(paris_tz)
                if next_exec > now:
                    diff_seconds = (next_exec - now).total_seconds()
                    time_remaining = f"{int(diff_seconds // 60)} min {int(diff_seconds % 60)} sec"
                else:
                    time_remaining = "very soon"
        except Exception as e:
            logging.error(f"Error formatting dates: {e}")

    return render_template(
        'index.html', 
        app_ready=app_ready,
        is_configured=is_configured,
        active_topic=active_topic,
        user_email=user_email,
        last_execution=last_execution,
        next_execution=next_execution,
        time_remaining=time_remaining
    )

@app.route('/api/status')
def api_status():
    """API endpoint for scheduler status (used by AJAX)"""
    scheduler_state = get_active_state()
    time_remaining = None
    next_execution = None
    
    if scheduler_state['next_execution']:
        try:
            paris_tz = pytz.timezone('Europe/Paris')
            next_exec = datetime.fromisoformat(scheduler_state['next_execution'])
            next_execution = next_exec.astimezone(paris_tz).strftime("%H:%M:%S")
            now = datetime.now(paris_tz)
            if next_exec > now:
                diff_seconds = (next_exec - now).total_seconds()
                time_remaining = f"{int(diff_seconds // 60)} min {int(diff_seconds % 60)} sec"
            else:
                time_remaining = "very soon"
        except Exception as e:
            logging.error(f"Error formatting API dates: {e}")

    return jsonify({
        "active": scheduler_state['active'],
        "topic": scheduler_state['topic'],
        "next_execution": next_execution,
        "time_remaining": time_remaining
    })

@app.route('/stop', methods=['POST'])
def stop_newsletter():
    """Stop the active newsletter"""
    stop_scheduling()
    session.pop('active_topic', None)
    flash('Monitoring stopped successfully.', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    load_dotenv()
    if os.getenv('TAVILY_API_KEY') and os.getenv('GEMINI_API_KEY'):
        config.load_credentials_from_env()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)