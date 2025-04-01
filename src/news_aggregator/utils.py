# src/news_aggregator/utils.py
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from . import config
# Avoid circular import - remove this line
# from graph import build_graph

def send_email(recipient_email: str, subject: str, body: str, html_body: str = None):
    """
    Send an email using the configured credentials.
    
    Args:
        recipient_email: The recipient's email address
        subject: The email subject
        body: The text content of the message (fallback)
        html_body: The HTML content of the message (optional)
    
    Returns:
        bool: True if sending was successful, False otherwise
    """
    if not config.SENDER_EMAIL or not config.SENDER_APP_PASSWORD or not recipient_email:
        logging.error("Email sending error: Missing sender or recipient information.")
        return False

    try:
        # Create message with HTML support
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        
        # Add text version (always first as fallback)
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # Add HTML version if available
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        context = ssl.create_default_context()

        logging.info(f"Attempting to connect to {config.SMTP_SERVER}:{config.SMTP_PORT}")
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls(context=context)  # Secure the connection
            logging.info("TLS connection established.")
            server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
            logging.info("SMTP login successful.")
            server.send_message(msg)
            logging.info(f"Email successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP authentication error. Check your email and application password.")
        return False
    except smtplib.SMTPConnectError:
         logging.error(f"Unable to connect to SMTP server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
         return False
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return False


def validate_email(email: str) -> bool:
    """
    Simple email address validation.
    
    Args:
        email: The email address to validate
        
    Returns:
        bool: True if the email appears valid, False otherwise
    """
    import re
    # Simple regular expression to check the basic format of an email
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def format_error_message(error_msg: str) -> str:
    """
    Format an error message for user display.
    Removes sensitive or overly complex technical details.
    
    Args:
        error_msg: The raw error message
        
    Returns:
        str: Error message formatted for the user
    """
    # If it's an API error, simplify
    if "API" in error_msg:
        return "API connection error. Check your API keys and internet connection."
    
    # If it's an email error
    if "SMTP" in error_msg or "email" in error_msg.lower():
        return "Email sending error. Check your email server settings."
    
    # Shorten overly long messages
    if len(error_msg) > 100:
        return error_msg[:97] + "..."
        
    return error_msg