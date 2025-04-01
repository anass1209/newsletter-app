# src/news_aggregator/config.py
import os
from dotenv import load_dotenv
import logging

# Basic logging setup (English)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
log = logging.getLogger(__name__)

# Load environment variables from a .env file if it exists
load_dotenv()
log.info(".env file loaded if present.")

def get_env_variable(var_name: str, default: str | None = None) -> str | None:
    """
    Retrieves an environment variable. Logs a warning if not found and no default is provided.

    Args:
        var_name: The name of the environment variable.
        default: The default value to return if the variable is not set.

    Returns:
        The value of the environment variable or the default value.
    """
    value = os.getenv(var_name, default)
    if value is None and default is None:
        log.warning(f"Environment variable '{var_name}' is not set and no default was provided.")
    elif value == default and default is not None:
         log.debug(f"Environment variable '{var_name}' not set, using default.")
    # else: value found or default is None (warning already logged)

    # Handle empty strings explicitly if needed, e.g., treat empty as None
    # if isinstance(value, str) and value.strip() == "":
    #     log.warning(f"Environment variable '{var_name}' is set but empty.")
    #     return default # Or None, depending on desired behavior

    return value

# --- Application Credentials and Settings ---

# API Keys (can be loaded from env or set via UI)
TAVILY_API_KEY: str | None = None
GEMINI_API_KEY: str | None = None

# Email Configuration
# User's email (recipient) - can be set via UI or env
USER_EMAIL: str | None = get_env_variable("USER_EMAIL")

# Sender email details (prefer loading from env for security)
SENDER_EMAIL: str | None = get_env_variable("SENDER_EMAIL")
SENDER_APP_PASSWORD: str | None = get_env_variable("SENDER_APP_PASSWORD") # Use App Password for Gmail/etc.
SMTP_SERVER: str = get_env_variable("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT: int = int(get_env_variable("SMTP_PORT", "587")) # 587 is standard for TLS

# Flask Configuration
FLASK_SECRET_KEY: str = get_env_variable("FLASK_SECRET_KEY", os.urandom(24).hex()) # Generate secure default
FLASK_DEBUG: bool = get_env_variable("FLASK_DEBUG", "False").lower() == "true"
FLASK_HOST: str = get_env_variable("FLASK_HOST", "0.0.0.0") # Default for Docker/cloud
FLASK_PORT: int = int(get_env_variable("FLASK_PORT", "5000"))

# --- Functions to Manage Credentials ---

def load_credentials_from_env() -> bool:
    """
    Loads API keys and sender email details directly from environment variables
    into the global config variables.

    Returns:
        bool: True if all required environment variables were found, False otherwise.
    """
    global TAVILY_API_KEY, GEMINI_API_KEY, SENDER_EMAIL, SENDER_APP_PASSWORD, USER_EMAIL

    log.info("Attempting to load credentials from environment variables...")
    tavily = get_env_variable("TAVILY_API_KEY")
    gemini = get_env_variable("GEMINI_API_KEY")
    sender = get_env_variable("SENDER_EMAIL")
    password = get_env_variable("SENDER_APP_PASSWORD")
    user = get_env_variable("USER_EMAIL") # Also load recipient email if set in env

    required_vars = {
        "TAVILY_API_KEY": tavily,
        "GEMINI_API_KEY": gemini,
        # Consider sender details optional if UI config is primary
        "SENDER_EMAIL": sender,
        "SENDER_APP_PASSWORD": password,
        # User email is often set via UI, but useful to have in env too
        "USER_EMAIL": user
    }

    missing = [name for name, value in required_vars.items() if not value]

    if not missing:
        TAVILY_API_KEY = tavily
        GEMINI_API_KEY = gemini
        SENDER_EMAIL = sender
        SENDER_APP_PASSWORD = password
        USER_EMAIL = user
        log.info("All required credentials found and loaded from environment variables.")
        return True
    else:
        # Only log warning if required ones are missing
        required_missing = [name for name in missing if name in ["TAVILY_API_KEY", "GEMINI_API_KEY"]] # Define what's truly required
        if required_missing:
             log.warning(f"Missing required environment variables for automatic configuration: {', '.join(required_missing)}. Configuration via UI may be needed.")
        else:
             log.info("Optional environment variables not set (e.g., SENDER_EMAIL, USER_EMAIL). Can be configured via UI.")
        # Load any partial creds found anyway
        TAVILY_API_KEY = tavily
        GEMINI_API_KEY = gemini
        SENDER_EMAIL = sender
        SENDER_APP_PASSWORD = password
        USER_EMAIL = user
        return False


def set_credentials(tavily_key: str | None, gemini_key: str | None, user_email: str | None,
                    sender_email: str | None = None, sender_password: str | None = None) -> bool:
    """
    Sets application credentials, typically from the web UI form.
    Updates the global config variables.

    Args:
        tavily_key: Tavily API Key.
        gemini_key: Gemini API Key.
        user_email: User's recipient email address.
        sender_email: Sender email address (optional, uses env if None).
        sender_password: Sender email app password (optional, uses env if None).

    Returns:
        bool: True if the essential keys (Tavily, Gemini, User Email) are provided, False otherwise.
              Logs warnings if sender details are missing but doesn't prevent setting API keys.
    """
    global TAVILY_API_KEY, GEMINI_API_KEY, USER_EMAIL, SENDER_EMAIL, SENDER_APP_PASSWORD

    valid_input = True
    if not tavily_key:
        log.error("Tavily API Key is missing in set_credentials call.")
        valid_input = False
    if not gemini_key:
        log.error("Gemini API Key is missing in set_credentials call.")
        valid_input = False
    if not user_email:
        log.error("User (recipient) Email is missing in set_credentials call.")
        valid_input = False

    if not valid_input:
        log.error("Cannot set credentials due to missing essential information.")
        return False

    log.info("Setting credentials from input (likely UI)...")
    TAVILY_API_KEY = tavily_key
    GEMINI_API_KEY = gemini_key
    USER_EMAIL = user_email

    # Update sender details only if provided, otherwise keep existing (from env or previous set)
    if sender_email:
        SENDER_EMAIL = sender_email
        log.info("Sender email updated.")
    elif not SENDER_EMAIL: # Check if it wasn't loaded from env either
         log.warning("Sender email was not provided and is not set in environment.")

    if sender_password:
        SENDER_APP_PASSWORD = sender_password
        log.info("Sender app password updated.")
    elif not SENDER_APP_PASSWORD: # Check if it wasn't loaded from env either
         log.warning("Sender app password was not provided and is not set in environment.")


    # Verify if email sending is possible after update
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        log.warning("Email sending functionality might be unavailable due to missing sender credentials.")
        # Decide if this should return False or just warn. Warning seems appropriate.

    log.info("Credentials updated in config module.")
    return True # Return True as long as essential API keys were set