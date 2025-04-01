import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Add app directory to Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(app_dir, 'src')

if app_dir not in sys.path:
    logging.info(f"Added root directory to Python path: {app_dir}")
    sys.path.insert(0, app_dir)

if src_dir not in sys.path:
    logging.info(f"Added src directory to Python path: {src_dir}")
    sys.path.insert(0, src_dir)

logging.info(f"Python path: {sys.path}")

try:
    # Import Flask app
    from src.news_aggregator import app as application
    logging.info("Successfully imported Flask app")
except Exception as e:
    logging.error(f"Error importing Flask app: {e}")
    raise

# Set debug mode based on environment
if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
    application.debug = True

# Handle WSGI application
if __name__ == '__main__':
    # Run app directly if executed
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)