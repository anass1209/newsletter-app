# wsgi.py
import sys
import os
import logging

# Setup basic logging (English)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Add the root directory to the Python path
root_dir = os.path.dirname(__file__)
sys.path.insert(0, root_dir)
logging.info(f"Added root directory to Python path: {root_dir}")

# Add the src directory to the Python path
src_dir = os.path.join(root_dir, 'src')
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)
    logging.info(f"Added src directory to Python path: {src_dir}")
else:
    logging.warning(f"src directory not found at: {src_dir}")

# Log the Python path for debugging
logging.info(f"Current Python path: {sys.path}")

# Create a function to get the Flask app instance
def get_app():
    """Imports and returns the Flask app instance."""
    try:
        # Import here to avoid potential circular dependencies during setup
        # and ensure paths are correctly configured first.
        from src.news_aggregator.app import app as flask_app
        logging.info("Successfully imported Flask app from src.news_aggregator.app")
        return flask_app
    except ImportError as e:
        logging.error(f"Failed to import Flask app: {e}")
        logging.error(f"Check if 'src.news_aggregator.app' exists and sys.path is correct: {sys.path}")
        # Attempt to provide more specific debug info
        try:
            import importlib
            spec = importlib.util.find_spec('src')
            logging.info(f"Found 'src' module spec: {spec}")
            spec_agg = importlib.util.find_spec('src.news_aggregator')
            logging.info(f"Found 'src.news_aggregator' module spec: {spec_agg}")
            spec_app = importlib.util.find_spec('src.news_aggregator.app')
            logging.info(f"Found 'src.news_aggregator.app' module spec: {spec_app}")
        except Exception as e2:
            logging.error(f"Error while checking module specifications: {e2}")
        raise  # Re-raise the original ImportError

# Expose the application for WSGI servers like Gunicorn
try:
    application = get_app()
    logging.info("Flask application successfully retrieved for WSGI server.")
except Exception as e:
    logging.critical(f"CRITICAL: Failed to initialize Flask app for WSGI: {e}")
    # Provide a minimal fallback WSGI app for graceful failure indication
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, headers)
        return [b'Application failed to start. Please check the server logs for details.']
    logging.info("Serving a fallback WSGI application due to initialization failure.")

# For local testing (e.g., python wsgi.py)
if __name__ == "__main__":
    logging.info("Running WSGI script directly for local testing.")
    try:
        # Ensure configuration is loaded if running directly
        from dotenv import load_dotenv
        load_dotenv()
        # Check if the app object is the real Flask app or the fallback
        if hasattr(application, 'run'):
             # Use Flask's built-in server for development
             # Note: For production, use Gunicorn: gunicorn wsgi:application
            host = os.getenv("FLASK_HOST", "127.0.0.1") # Default to localhost for local run
            port = int(os.getenv("FLASK_PORT", 5001)) # Use a different port maybe
            debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
            logging.info(f"Starting Flask development server on {host}:{port} (Debug: {debug})")
            application.run(host=host, port=port, debug=debug)
        else:
            logging.warning("Cannot run the fallback application directly. Exiting.")
    except Exception as e:
        logging.critical(f"Error running Flask app locally: {e}")