from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import logging
from datetime import datetime, timezone
import pytz # For display formatting
import secrets
from dotenv import load_dotenv
import atexit
import humanize # For user-friendly time differences

# Import local modules using relative paths within the package
from .graph import build_graph
from .scheduler import start_scheduling, stop_scheduling, get_active_state
from .config import set_credentials, load_credentials_from_env, get_env_variable
from .utils import validate_email, format_error_message # Import utility functions

# Load environment variables early
load_dotenv()

# Logging setup (English)
# Use the root logger configured in wsgi.py or configure specifically
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s')
log = logging.getLogger(__name__) # Use a specific logger for this module

# Flask app initialization
app = Flask(__name__,
            static_folder='static',   # Relative path within the package
            template_folder='templates' # Relative path within the package
            )
app.secret_key = get_env_variable('FLASK_SECRET_KEY', secrets.token_hex(16)) # Use a secure default
log.info("Flask app initialized.")

# Attempt to load credentials from .env on startup
# This allows running without UI configuration if .env is set
env_creds_loaded = load_credentials_from_env()
if env_creds_loaded:
    log.info("Credentials successfully loaded from environment variables.")
    session['configured'] = True # Mark as configured if loaded from env
    session['user_email'] = get_env_variable("USER_EMAIL") # Load user email from env too
else:
    log.info("Environment variables for credentials not fully set. Configuration via UI might be needed.")

# Compile LangGraph once at startup
compiled_graph = None
try:
    log.info("Attempting to build and compile LangGraph...")
    compiled_graph = build_graph()
    log.info("LangGraph compiled successfully.")
except Exception as e:
    log.exception("CRITICAL: Failed to compile LangGraph at startup. The core functionality might be unavailable.")
    # The app will still run, but the index page will show an error state.

# Ensure scheduler stops cleanly on application exit
def cleanup_scheduler():
    log.info("Application exiting. Ensuring scheduler is stopped...")
    stop_scheduling()
    log.info("Scheduler stop requested during application cleanup.")
atexit.register(cleanup_scheduler)
log.info("Registered scheduler cleanup function with atexit.")


# == Routes ==

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the main page: configuration, topic submission, and status display."""
    global compiled_graph # Allow potentially retrying graph compilation

    # Check if graph compilation failed earlier
    if compiled_graph is None:
        log.warning("Rendering index page, but LangGraph is not compiled.")
        # Optionally try to recompile? Or just show error.
        # flash('Critical Error: The core processing graph could not be initialized. Please check logs.', 'danger')
        pass # The template will handle the 'app_ready' flag

    if request.method == 'POST':
        log.debug(f"POST request received on / route. Form data: {request.form}")
        # --- Handle Configuration Submission ---
        if 'setup_config' in request.form:
            log.info("Handling configuration form submission.")
            tavily_key = request.form.get('tavily_api_key', '').strip()
            gemini_key = request.form.get('gemini_api_key', '').strip()
            user_email = request.form.get('user_email', '').strip()
            sender_email = request.form.get('sender_email', '').strip() # Assuming these are added to form
            sender_password = request.form.get('sender_app_password', '').strip() # Assuming these are added

            # Basic Validation
            errors = []
            if not tavily_key: errors.append("Tavily API Key is required.")
            if not gemini_key: errors.append("Gemini API Key is required.")
            if not user_email: errors.append("Your Email Address (Recipient) is required.")
            if not validate_email(user_email): errors.append("Invalid recipient email format.")
            # Optional: Validate sender email if provided through UI
            # if sender_email and not validate_email(sender_email): errors.append("Invalid sender email format.")

            if errors:
                for error in errors:
                    flash(error, 'danger')
                log.warning(f"Configuration submission failed validation: {errors}")
                # Return the form with errors, potentially preserving input?
                # For simplicity, just redirecting back to the GET view.
                return redirect(url_for('index'))

            log.info(f"Configuration received for user: {user_email}")
            # Use config module to set credentials
            creds_set = set_credentials(
                tavily_key=tavily_key,
                gemini_key=gemini_key,
                user_email=user_email,
                sender_email=sender_email or None, # Pass None if empty
                sender_password=sender_password or None # Pass None if empty
            )

            if creds_set:
                session['user_email'] = user_email
                session['configured'] = True
                flash('Configuration saved successfully!', 'success')
                log.info("Configuration saved to session and config module.")
                # Re-attempt graph build if it failed previously and config looks ok
                if compiled_graph is None:
                     log.info("Configuration updated, attempting to rebuild LangGraph...")
                     try:
                         compiled_graph = build_graph()
                         log.info("LangGraph successfully rebuilt after configuration.")
                         flash('Core services initialized successfully.', 'info')
                     except Exception as e:
                         log.exception("CRITICAL: Failed to rebuild LangGraph after configuration.")
                         flash('Configuration saved, but failed to initialize core services. Check logs.', 'danger')
            else:
                flash('Failed to save configuration. Check logs for details.', 'danger')
                log.error("set_credentials reported failure.")

            return redirect(url_for('index'))

        # --- Handle Topic Submission ---
        elif 'start_monitoring' in request.form:
            topic = request.form.get('topic', '').strip()
            log.info(f"Handling topic submission. Topic: '{topic}'")

            if not topic:
                log.warning("Topic submission received with empty topic.")
                flash('Please enter a topic to monitor.', 'warning')
                return redirect(url_for('index'))

            if not session.get('configured') or not session.get('user_email'):
                log.warning("Attempt to start monitoring without prior configuration.")
                flash('Please configure your API keys and email address first.', 'warning')
                return redirect(url_for('index'))

            if compiled_graph is None:
                log.error("Attempt to start monitoring, but LangGraph is not compiled.")
                flash('Error: The monitoring service is not ready. Please check configuration or server logs.', 'danger')
                return redirect(url_for('index'))

            current_user_email = session['user_email']
            log.info(f"Attempting to start monitoring for topic '{topic}' for user '{current_user_email}'.")

            try:
                # Stop any existing scheduler first
                if get_active_state()['active']:
                    log.info("Stopping existing scheduler before starting a new one.")
                    stop_scheduling()
                    # Add a small delay to ensure the thread fully stops if needed
                    import time
                    time.sleep(0.5)

                # Start scheduling (DAILY = 24 hours)
                interval = 24 # Hours for daily
                success = start_scheduling(compiled_graph, topic, current_user_email, interval_hours=interval)

                if success:
                    session['active_topic'] = topic # Store active topic in session
                    flash(f'Monitoring started for "{topic}". The first newsletter is being generated and will be sent shortly. Subsequent updates will be daily.', 'success')
                    log.info(f"Successfully started daily monitoring for topic: {topic}")
                else:
                    flash('Error: Could not start the monitoring service. Check server logs.', 'danger')
                    log.error(f"start_scheduling failed for topic '{topic}'.")

            except Exception as e:
                error_msg = f"An unexpected error occurred while starting monitoring for topic '{topic}': {str(e)}"
                log.exception(error_msg) # Log the full traceback
                flash(format_error_message(f'Error starting monitoring: {str(e)}'), 'danger')

            return redirect(url_for('index'))

    # --- Handle GET Request ---
    scheduler_state = get_active_state()
    log.debug(f"GET request on / route. Scheduler state: {scheduler_state}")

    # Sync session with scheduler state (if scheduler stops externally, session should reflect it)
    if scheduler_state.get('active') and scheduler_state.get('topic'):
        session['active_topic'] = scheduler_state['topic']
        # Ensure user email in session matches scheduler state if possible
        if session.get('user_email') != scheduler_state.get('user_email'):
             log.warning("Session email and scheduler email mismatch. Updating session.")
             session['user_email'] = scheduler_state.get('user_email')
    elif not scheduler_state.get('active') and session.get('active_topic'):
         log.info("Scheduler is inactive, removing active_topic from session.")
         session.pop('active_topic', None)


    # Prepare data for template
    app_ready = bool(compiled_graph)
    # Check config status based on session OR if creds loaded from env initially
    is_configured = session.get('configured', env_creds_loaded)
    active_topic = session.get('active_topic', None) # Get from session now
    user_email = session.get('user_email', '')

    # Format timing information for display (use UTC from state, format to local)
    display_last_execution = None
    display_next_execution = None
    next_execution_iso_utc = None # For JS timer
    time_until_next = None
    status_message = scheduler_state.get('status_message', "Scheduler status unknown.")

    try:
        target_tz = pytz.timezone('Europe/Paris') # Example: User's local timezone
        now_local = datetime.now(target_tz)

        if scheduler_state.get('last_execution'):
            last_exec_utc = datetime.fromisoformat(scheduler_state['last_execution'].replace('Z', '+00:00'))
            display_last_execution = last_exec_utc.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

        if scheduler_state.get('next_execution'):
            next_exec_utc = datetime.fromisoformat(scheduler_state['next_execution'].replace('Z', '+00:00'))
            next_execution_iso_utc = scheduler_state['next_execution'] # Pass ISO UTC to JS
            display_next_execution = next_exec_utc.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

            # Calculate human-readable time difference using current local time
            now_utc = datetime.now(timezone.utc)
            if next_exec_utc > now_utc:
                 # Use humanize for friendly difference
                 time_until_next = humanize.naturaltime(next_exec_utc - now_utc) + f" (approx)"
                 # Alternatively, calculate minutes/seconds if preferred for short intervals
                 # diff_seconds = (next_exec_utc - now_utc).total_seconds()
                 # minutes = int(diff_seconds // 60)
                 # seconds = int(diff_seconds % 60)
                 # time_until_next = f"{minutes} min {seconds} sec"
            else:
                 time_until_next = "due now or very soon"

    except Exception as e:
        log.error(f"Error formatting dates for display: {e}")
        # Log the problematic date strings if possible
        log.error(f"Problematic dates - Last: {scheduler_state.get('last_execution')}, Next: {scheduler_state.get('next_execution')}")


    return render_template(
        'index.html',
        app_ready=app_ready,
        is_configured=is_configured,
        active_topic=active_topic,
        user_email=user_email,
        # Pass formatted dates and times
        last_execution_str=display_last_execution,
        next_execution_str=display_next_execution,
        next_execution_iso_utc=next_execution_iso_utc, # UTC ISO for JS
        time_until_next_str=time_until_next,
        scheduler_status_message=status_message # Pass status message
    )


@app.route('/api/status')
def api_status():
    """API endpoint to get the current scheduler status (used by AJAX)."""
    scheduler_state = get_active_state()
    log.debug(f"API request for status. Current state: {scheduler_state}")

    response_data = {
        "active": scheduler_state.get('active', False),
        "topic": scheduler_state.get('topic'),
        "last_execution_utc": scheduler_state.get('last_execution'),
        "next_execution_utc": scheduler_state.get('next_execution'), # ISO UTC for JS
        "status_message": scheduler_state.get('status_message', "Status unavailable."),
        "server_time_utc": datetime.now(timezone.utc).isoformat()
    }

    # Calculate time remaining dynamically for the API response
    time_remaining_str = None
    if scheduler_state.get('next_execution'):
        try:
            next_exec_utc = datetime.fromisoformat(scheduler_state['next_execution'].replace('Z', '+00:00'))
            now_utc = datetime.now(timezone.utc)
            if next_exec_utc > now_utc:
                time_remaining_str = humanize.naturaltime(next_exec_utc - now_utc) + " (approx)"
            else:
                time_remaining_str = "due now or very soon"
        except Exception as e:
            log.error(f"Error calculating time remaining in API: {e}")
            time_remaining_str = "Error calculating"

    response_data["time_until_next_str"] = time_remaining_str

    return jsonify(response_data)

@app.route('/stop', methods=['POST'])
def stop_newsletter():
    """Stops the active newsletter monitoring schedule."""
    log.info("Received request to stop monitoring.")
    try:
        stopped = stop_scheduling()
        if stopped:
            session.pop('active_topic', None) # Clear from session too
            flash('Monitoring stopped successfully.', 'success')
            log.info("Monitoring stopped via /stop route.")
        else:
            flash('No active monitoring process was found to stop.', 'info')
            log.info("Attempted to stop monitoring, but scheduler was not active.")
    except Exception as e:
        error_msg = f"An error occurred while trying to stop monitoring: {str(e)}"
        log.exception(error_msg)
        flash(format_error_message(f'Error stopping monitoring: {str(e)}'), 'danger')

    return redirect(url_for('index'))


# == Error Handlers ==

@app.errorhandler(404)
def page_not_found(e):
    log.warning(f"404 Not Found error for URL: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    log.error(f"500 Internal Server Error: {e}", exc_info=True) # Log the exception
    return render_template('500.html'), 500

# == Main Execution ==
if __name__ == '__main__':
    # This block is mainly for local development.
    # In production, use a WSGI server like Gunicorn (e.g., gunicorn wsgi:application)
    log.info("Running Flask app directly for development.")
    # Debug is often enabled via FLASK_DEBUG env var
    port = int(get_env_variable("FLASK_PORT", 5000))
    host = get_env_variable("FLASK_HOST", "127.0.0.1") # Default to localhost for direct run
    debug_mode = get_env_variable("FLASK_DEBUG", "False").lower() == "true"
    log.info(f"Starting development server on http://{host}:{port}/ (Debug: {debug_mode})")
    app.run(host=host, port=port, debug=debug_mode)
