import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Add app directory to Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(app_dir, 'src')

# Ensure src is in the path first
if src_dir not in sys.path:
    logging.info(f"Added src directory to Python path: {src_dir}")
    sys.path.insert(0, src_dir)

# Add the app directory to path
if app_dir not in sys.path:
    logging.info(f"Added root directory to Python path: {app_dir}")
    sys.path.insert(0, app_dir)

logging.info(f"Python path: {sys.path}")

try:
    # Import Flask app directly
    from src.news_aggregator import app as application
    # THIS IS THE KEY: ensure the app is exported as 'application'
    application = application  # Make sure application variable is defined
    logging.info("Successfully imported Flask app")
except ImportError:
    logging.error("Failed to import app directly, trying alternative import path")
    try:
        # Try alternative import path
        from src.news_aggregator import app as application
        application = application  # Ensure application variable is defined
        logging.info("Successfully imported Flask app via alternative path")
    except Exception as e:
        logging.error(f"Error importing Flask app: {e}")
        raise

# Set debug mode based on environment
if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
    application.debug = True

# Check if application is callable (as required by WSGI)
if not callable(application):
    logging.error("Application is not callable! Type: %s", type(application))
    # Convert Flask app to a callable if needed
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    application = DispatcherMiddleware(application)

# This section only runs when executing wsgi.py directly
if __name__ == '__main__':
    # Run app directly if executed
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)