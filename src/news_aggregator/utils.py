# src/news_aggregator/utils.py
import smtplib
import ssl
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from . import config
from graph import build_graph

def send_email(recipient_email: str, subject: str, body: str, html_body: str = None):
    """
    Envoie un email en utilisant les credentials configurés.
    
    Args:
        recipient_email: L'adresse email du destinataire
        subject: Le sujet du message
        body: Le contenu texte du message (fallback)
        html_body: Le contenu HTML du message (optionnel)
    
    Returns:
        bool: True si l'envoi a réussi, False sinon
    """
    if not config.SENDER_EMAIL or not config.SENDER_APP_PASSWORD or not recipient_email:
        logging.error("Erreur d'envoi d'email: Informations d'expéditeur ou de destinataire manquantes.")
        return False

    try:
        # Création du message avec support HTML
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        
        # Ajouter la version texte (toujours en premier comme fallback)
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # Ajouter la version HTML si disponible
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        context = ssl.create_default_context()

        logging.info(f"Tentative de connexion à {config.SMTP_SERVER}:{config.SMTP_PORT}")
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls(context=context)  # Sécurise la connexion
            logging.info("Connexion TLS établie.")
            server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
            logging.info("Login SMTP réussi.")
            server.send_message(msg)
            logging.info(f"Email envoyé avec succès à {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logging.error("Erreur d'authentification SMTP. Vérifiez l'email et le mot de passe d'application.")
        return False
    except smtplib.SMTPConnectError:
         logging.error(f"Impossible de se connecter au serveur SMTP: {config.SMTP_SERVER}:{config.SMTP_PORT}")
         return False
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email: {e}")
        return False


def validate_email(email: str) -> bool:
    """
    Validation simple d'adresse email.
    
    Args:
        email: L'adresse email à valider
        
    Returns:
        bool: True si l'email semble valide, False sinon
    """
    import re
    # Expression régulière simple pour vérifier le format de base d'un email
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def format_error_message(error_msg: str) -> str:
    """
    Formate un message d'erreur pour l'affichage à l'utilisateur.
    Supprime les détails techniques sensibles ou trop complexes.
    
    Args:
        error_msg: Le message d'erreur brut
        
    Returns:
        str: Message d'erreur formaté pour l'utilisateur
    """
    # Si c'est une erreur d'API, simplifier
    if "API" in error_msg:
        return "Erreur de connexion API. Vérifiez vos clés API et votre connexion internet."
    
    # Si c'est une erreur d'email
    if "SMTP" in error_msg or "email" in error_msg.lower():
        return "Erreur d'envoi d'email. Vérifiez les paramètres de votre serveur mail."
    
    # Raccourcir les messages trop longs
    if len(error_msg) > 100:
        return error_msg[:97] + "..."
        
    return error_msg