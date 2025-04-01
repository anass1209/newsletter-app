# wsgi.py
import sys
import os
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Add root directory to Python path
root_dir = os.path.dirname(__file__)
sys.path.insert(0, root_dir)
logging.info(f"Added root directory to Python path: {root_dir}")

# Add src directory to Python path
src_dir = os.path.join(root_dir, 'src')
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)
    logging.info(f"Added src directory to Python path: {src_dir}")

# Log the Python path for debugging
logging.info(f"Python path: {sys.path}")

# Create a function for the Flask application
def get_app():
    try:
        # Import here to avoid circular reference errors
        from src.news_aggregator.app import app as flask_app
        logging.info("Successfully imported Flask app")
        return flask_app
    except ImportError as e:
        logging.error(f"Failed to import Flask app: {e}")
        # Try to determine what went wrong
        try:
            import importlib
            spec = importlib.util.find_spec('src.news_aggregator')
            logging.info(f"src.news_aggregator module spec: {spec}")
        except Exception as e2:
            logging.error(f"Error checking module spec: {e2}")
        raise

# Expose the application for Gunicorn
try:
    application = get_app()
except Exception as e:
    logging.critical(f"Failed to get Flask app: {e}")
    # Provide a basic WSGI app for fallback
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/plain; charset=utf-8')]
        start_response(status, headers)
        return [b'Application failed to start. Check logs for details.']

# For local testing
if __name__ == "__main__":
    try:
        application.run()
    except Exception as e:
        logging.critical(f"Error running Flask app: {e}")