# src/news_aggregator/utils.py
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import re

# Import config using relative path
from . import config

# Logging setup (English)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
log = logging.getLogger(__name__)

def send_email(recipient_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """
    Sends an email using the configured SMTP credentials.

    Args:
        recipient_email: The recipient's email address.
        subject: The email subject line.
        body: The plain text content of the email (used as fallback).
        html_body: The HTML content of the email (optional, preferred if available).

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # --- Input Validation ---
    if not recipient_email:
        log.error("Email sending failed: Recipient email address is missing.")
        return False
    if not validate_email(recipient_email):
         log.error(f"Email sending failed: Invalid recipient email format '{recipient_email}'.")
         return False
    if not config.SENDER_EMAIL or not config.SENDER_APP_PASSWORD:
        log.error("Email sending failed: Sender email address or application password is not configured.")
        # Consider adding more specific guidance, e.g., "Check SENDER_EMAIL and SENDER_APP_PASSWORD in config or .env"
        return False
    if not subject:
         log.warning("Sending email with an empty subject line.")
         subject = "(No Subject)" # Provide a default subject

    log.info(f"Preparing to send email. To: {recipient_email}, Subject: '{subject[:50]}...'") # Log truncated subject

    try:
        # Create the email message object
        # Use MIMEMultipart("alternative") for emails with both HTML and plain text
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        # Optional: Add Reply-To header
        # msg['Reply-To'] = config.SENDER_EMAIL

        # Attach the plain text part first (important for compatibility)
        # Ensure body is properly encoded
        plain_part = MIMEText(body, "plain", "utf-8")
        msg.attach(plain_part)
        log.debug("Plain text part attached to email.")

        # Attach the HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)
            log.debug("HTML part attached to email.")
        else:
            log.warning("No HTML body provided for email, sending plain text only.")


        # --- SMTP Connection and Sending ---
        # Use default SSL context for security
        context = ssl.create_default_context()

        smtp_server = config.SMTP_SERVER
        smtp_port = config.SMTP_PORT
        sender_email = config.SENDER_EMAIL
        sender_password = config.SENDER_APP_PASSWORD # Should be App Password

        log.info(f"Attempting SMTP connection to {smtp_server}:{smtp_port}...")
        # Use 'with' statement for automatic connection closing
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            log.debug("SMTP connection established.")
            # Secure the connection with STARTTLS
            server.starttls(context=context)
            log.info("STARTTLS command successful, connection secured.")
            # Login to the sender's account
            server.login(sender_email, sender_password)
            log.info(f"SMTP login successful for user {sender_email}.")
            # Send the email
            server.send_message(msg)
            log.info(f"Email successfully sent to {recipient_email}.")

        return True

    except smtplib.SMTPAuthenticationError as e:
        log.error(f"SMTP Authentication Error: Failed to authenticate with {sender_email}. Check email/password (use App Password for Gmail). Error: {e}")
        return False
    except smtplib.SMTPConnectError as e:
         log.error(f"SMTP Connection Error: Failed to connect to server {smtp_server}:{smtp_port}. Check server/port and network. Error: {e}")
         return False
    except smtplib.SMTPServerDisconnected as e:
         log.error(f"SMTP Server Disconnected unexpectedly. Error: {e}")
         return False
    except smtplib.SMTPException as e: # Catch other potential SMTP errors
         log.error(f"An SMTP error occurred: {e}")
         return False
    except ConnectionRefusedError as e:
         log.error(f"Connection Refused: Could not connect to {smtp_server}:{smtp_port}. Is the server running/accessible? Error: {e}")
         return False
    except OSError as e: # Catch potential network errors like [Errno 101] Network is unreachable
        log.error(f"Network or OS error during email sending: {e}")
        return False
    except Exception as e:
        # Catch any other unexpected errors during the process
        log.exception(f"An unexpected error occurred during email sending: {e}") # Log full traceback
        return False


def validate_email(email: str) -> bool:
    """
    Performs a basic validation of an email address format using regex.

    Args:
        email: The email address string to validate.

    Returns:
        bool: True if the email format looks valid, False otherwise.
    """
    if not email:
        return False
    # A commonly used regex for basic email format validation
    # It's not foolproof (RFC 5322 is complex) but covers most common cases.
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Explanation:
    # ^                    - Start of string
    # [a-zA-Z0-9._%+-]+   - One or more alphanumeric characters or ._%+- (local part)
    # @                    - Literal "@" symbol
    # [a-zA-Z0-9.-]+       - One or more alphanumeric characters or .- (domain name part)
    # \.                   - Literal "." symbol
    # [a-zA-Z]{2,}         - Two or more alphabetic characters (top-level domain)
    # $                    - End of string
    if re.match(pattern, email):
        return True
    else:
        log.debug(f"Email validation failed for: {email}")
        return False


def format_error_message(error_msg: str) -> str:
    """
    Formats a potentially technical error message into a more user-friendly version
    for display in the UI (e.g., via flash messages).

    Args:
        error_msg: The original error message string.

    Returns:
        A simplified, user-friendly error message string.
    """
    if not error_msg:
        return "An unknown error occurred."

    error_lower = error_msg.lower()

    # Simplify common technical errors
    if "api key" in error_lower or "authentication" in error_lower and "api" in error_lower:
        return "API Key Error. Please check your Tavily and Gemini API keys in the configuration."
    if "tavily" in error_lower and "failed" in error_lower:
         return "Tavily Search Error. Could not fetch data. Check API key or Tavily status."
    if "gemini" in error_lower or "generativemodel" in error_lower:
         return "Gemini AI Error. Could not process content. Check API key or Google AI status."
    if "smtp" in error_lower or "email" in error_lower or "mail" in error_lower:
        if "authentication" in error_lower:
             return "Email Sending Error: Authentication failed. Please verify sender email and App Password."
        elif "connect" in error_lower or "connection refused" in error_lower:
             return "Email Sending Error: Could not connect to the mail server. Check SMTP settings and network."
        else:
            return "Email Sending Error. Please check your email configuration and server status."
    if "network is unreachable" in error_lower or "connection timed out" in error_lower:
        return "Network Error. Could not connect to external services. Please check your internet connection."
    if "recipient email missing" in error_lower:
         return "Configuration Error: Recipient email address is not set."
    if "blocked by safety filters" in error_lower or "response blocked" in error_lower:
        return "Content Generation Error: The AI service blocked the request due to safety filters. Try refining the topic."

    # Default simplification for long or generic errors
    if len(error_msg) > 150: # Shorten very long messages
        return error_msg[:147] + "..."

    # If no specific pattern matched, return the original message (or a generic one)
    # return error_msg # Option 1: Return original if not matched
    return f"An error occurred: {error_msg}" # Option 2: Prefix with generic text