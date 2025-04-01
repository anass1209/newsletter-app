# src/news_aggregator/utils.py
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import time
from . import config
import re

def send_email(recipient_email: str, subject: str, body: str, html_body: str = None):
    """
    Send an email using configured credentials.
    
    Args:
        recipient_email: The recipient's email address
        subject: The message subject
        body: The plain text content of the message (fallback)
        html_body: The HTML content of the message (optional)
    
    Returns:
        bool: True if sending succeeded, False otherwise
    """
    if not config.SENDER_EMAIL or not config.SENDER_APP_PASSWORD or not recipient_email:
        logging.error("Email sending error: Missing sender information.")
        logging.error(f"Sender email exists: {bool(config.SENDER_EMAIL)}")
        logging.error(f"Sender password exists: {bool(config.SENDER_APP_PASSWORD)}")
        logging.error(f"Recipient email exists: {bool(recipient_email)}")
        return False

    try:
        # Create message with HTML support
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        
        # Add plain text version first (fallback)
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # Add HTML version if available
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        # Create secure SSL context
        context = ssl.create_default_context()

        logging.info(f"Connecting to {config.SMTP_SERVER}:{config.SMTP_PORT}")
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.ehlo()  # Can help with connection issues
            server.starttls(context=context)  # Secure the connection
            logging.info("TLS connection established")
            server.ehlo()  # Re-identify after TLS
            server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
            logging.info("SMTP login successful")
            server.send_message(msg)
            logging.info(f"Email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as auth_error:
        logging.error(f"SMTP Authentication Error: {auth_error}")
        logging.error("Check your sender email and app password")
        return False
    except smtplib.SMTPConnectError as conn_error:
        logging.error(f"SMTP Connection Error: {conn_error}")
        logging.error(f"Unable to connect to SMTP server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
        return False
    except smtplib.SMTPServerDisconnected as disc_error:
        logging.error(f"SMTP Server Disconnected: {disc_error}")
        logging.error("Server unexpectedly disconnected")
        return False
    except smtplib.SMTPException as smtp_error:
        logging.error(f"SMTP Error: {smtp_error}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending email: {str(e)}")
        return False


def validate_email(email: str) -> bool:
    """
    Simple email address validation.
    
    Args:
        email: The email address to validate
        
    Returns:
        bool: True if the email appears valid, False otherwise
    """
    # More comprehensive regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False
    return bool(re.match(pattern, email))


def format_error_message(error_msg: str) -> str:
    """
    Format an error message for user display.
    Removes sensitive technical details.
    
    Args:
        error_msg: The raw error message
        
    Returns:
        str: User-friendly error message
    """
    # API key related errors
    if "API key" in error_msg:
        return "API connection error. Please check your API keys and try again."
    
    # Email related errors
    if any(term in error_msg.lower() for term in ["smtp", "email", "authentication"]):
        return "Email sending error. Please check email settings and try again."
    
    # Service timeout errors
    if any(term in error_msg.lower() for term in ["timeout", "timed out", "connection"]):
        return "Service timeout. Our servers are busy, please try again shortly."
    
    # Shorten overly long messages
    if len(error_msg) > 100:
        return error_msg[:97] + "..."
        
    return error_msg


def retry_with_backoff(func, max_retries=3, initial_backoff=1):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to call
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff time in seconds
    
    Returns:
        Result of the function or raises the last exception
    """
    retries = 0
    backoff = initial_backoff
    
    while retries < max_retries:
        try:
            return func()
        except Exception as e:
            retries += 1
            if retries == max_retries:
                raise e
            
            logging.warning(f"Attempt {retries} failed: {str(e)}. Retrying in {backoff} seconds...")
            time.sleep(backoff)
            # Exponential backoff
            backoff *= 2