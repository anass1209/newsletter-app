import os
from dotenv import load_dotenv
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env
load_dotenv()

def get_env_variable(var_name: str, default=None) -> str:
    """Retrieve an environment variable with an optional default value."""
    value = os.getenv(var_name, default)
    if value is None:
        logging.warning(f"Environment variable '{var_name}' not set.")
    return value

# API keys (initially None, loaded from env or web UI)
TAVILY_API_KEY: str | None = None
GEMINI_API_KEY: str | None = None

# Email configuration
USER_EMAIL: str | None = None  # Recipient email (user)
SENDER_EMAIL: str | None = get_env_variable("SENDER_EMAIL", "default@example.com")
SENDER_APP_PASSWORD: str | None = get_env_variable("SENDER_APP_PASSWORD")
SMTP_SERVER: str = get_env_variable("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT: int = int(get_env_variable("SMTP_PORT", "587"))

# Flask configuration
FLASK_SECRET_KEY: str = get_env_variable("FLASK_SECRET_KEY", os.urandom(24).hex())
FLASK_DEBUG: bool = get_env_variable("FLASK_DEBUG", "False").lower() == "true"
FLASK_HOST: str = get_env_variable("FLASK_HOST", "0.0.0.0")
FLASK_PORT: int = int(get_env_variable("FLASK_PORT", "5000"))

def load_credentials_from_env():
    """Load credentials from environment variables."""
    global TAVILY_API_KEY, GEMINI_API_KEY, SENDER_EMAIL, SENDER_APP_PASSWORD
    
    TAVILY_API_KEY = get_env_variable("TAVILY_API_KEY")
    GEMINI_API_KEY = get_env_variable("GEMINI_API_KEY")
    SENDER_EMAIL = get_env_variable("SENDER_EMAIL", "default@example.com")
    SENDER_APP_PASSWORD = get_env_variable("SENDER_APP_PASSWORD")
    
    if all([TAVILY_API_KEY, GEMINI_API_KEY, SENDER_EMAIL, SENDER_APP_PASSWORD]):
        logging.info("Credentials loaded from environment variables.")
        return True
    else:
        missing = [var for var, val in {
            "TAVILY_API_KEY": TAVILY_API_KEY,
            "GEMINI_API_KEY": GEMINI_API_KEY,
            "SENDER_EMAIL": SENDER_EMAIL,
            "SENDER_APP_PASSWORD": SENDER_APP_PASSWORD
        }.items() if not val]
        logging.warning(f"Missing variables: {', '.join(missing)}")
        return False

def set_credentials(tavily_key: str, gemini_key: str, user_email: str, sender_email: str = None, sender_password: str = None):
    """Set application credentials."""
    global TAVILY_API_KEY, GEMINI_API_KEY, USER_EMAIL, SENDER_EMAIL, SENDER_APP_PASSWORD
    
    # Log start of credential setting with partial key masking
    tavily_masked = tavily_key[:4] + "*****" if tavily_key else "None"
    gemini_masked = gemini_key[:4] + "*****" if gemini_key else "None"
    logging.info(f"Setting credentials - Tavily: {tavily_masked}, Gemini: {gemini_masked}, Email: {user_email}")
    
    # Set values to globals
    TAVILY_API_KEY = tavily_key
    GEMINI_API_KEY = gemini_key
    USER_EMAIL = user_email
    
    if sender_email:
        SENDER_EMAIL = sender_email
    if sender_password:
        SENDER_APP_PASSWORD = sender_password
    
    # Verify values have been set
    tavily_set = bool(TAVILY_API_KEY)
    gemini_set = bool(GEMINI_API_KEY)
    user_set = bool(USER_EMAIL)
    
    logging.info(f"Credentials set status - Tavily: {tavily_set}, Gemini: {gemini_set}, User Email: {user_set}")
    
    # Create or update an environment file for persistence
    try:
        with open('.env.local', 'w') as f:
            f.write(f"TAVILY_API_KEY={TAVILY_API_KEY or ''}\n")
            f.write(f"GEMINI_API_KEY={GEMINI_API_KEY or ''}\n")
            f.write(f"USER_EMAIL={USER_EMAIL or ''}\n")
            if SENDER_EMAIL:
                f.write(f"SENDER_EMAIL={SENDER_EMAIL}\n")
            if SENDER_APP_PASSWORD:
                f.write(f"SENDER_APP_PASSWORD={SENDER_APP_PASSWORD}\n")
        logging.info("Credentials written to .env.local file for persistence")
    except Exception as e:
        logging.warning(f"Could not write credentials to .env.local file: {e}")
        
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        logging.warning("Sender email or password missing.")
        return False
    return True