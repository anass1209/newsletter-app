# src/scheduler.py
import schedule
import time
import logging
import threading
from datetime import datetime
import pytz
from langgraph.graph import StateGraph
from news_aggregator.graph import GraphState

# Variables globales pour contrôler le scheduler
stop_scheduler = threading.Event()
scheduler_thread = None
active_topic = None
active_email = None
last_execution_time = None
next_execution_time = None

def run_graph_job(compiled_graph: StateGraph, topic: str, user_email: str):
    """
    Fonction exécutée par le scheduler pour invoquer le graphe.
    Génère et envoie une newsletter basée sur le sujet spécifié.
    
    Args:
        compiled_graph: Le graphe LangGraph compilé
        topic: Le sujet de la newsletter
        user_email: L'email du destinataire
    """
    global active_topic, active_email, last_execution_time, next_execution_time
    
    # Enregistrer le moment d'exécution avec l'heure locale correcte
    paris_tz = pytz.timezone('Europe/Paris')
    last_execution_time = datetime.now(paris_tz)
    
    # Calculer la prochaine exécution (exactement 1 heure après)
    next_execution_time = last_execution_time.replace(
        minute=0, 
        second=0, 
        microsecond=0
    )
    
    # S'assurer que c'est une heure plus tard
    if next_execution_time <= last_execution_time:
        next_execution_time = next_execution_time.replace(hour=next_execution_time.hour + 1)
    
    logging.info(f"--- Début de l'exécution planifiée pour le sujet: '{topic}' à {last_execution_time.strftime('%H:%M:%S')} ---")
    try:
        # Initialisation de l'état avec des valeurs vides
        initial_state = GraphState(
            topic=topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=user_email,
            timestamp=last_execution_time.strftime("%d/%m/%Y à %H:%M")
        )
        
        # Invoquer le graphe avec l'état initial
        result_state = compiled_graph.invoke(initial_state)

        if result_state.get("error"):
            logging.error(f"Erreur lors de l'exécution du graphe : {result_state['error']}")
        else:
            logging.info(f"--- Newsletter générée et envoyée pour : '{topic}' à {user_email} ---")
            logging.info(f"--- Prochaine exécution prévue à : {next_execution_time.strftime('%H:%M')} ---")
            
            # Mettre à jour les variables globales pour suivre l'état actif
            active_topic = topic
            active_email = user_email

    except Exception as e:
        logging.exception(f"Erreur majeure lors de l'exécution du job pour '{topic}': {e}")


def start_scheduling(compiled_graph: StateGraph, topic: str, user_email: str, interval_hours: float = 1.0):
    """
    Configure et démarre le scheduling dans un thread séparé.
    
    Args:
        compiled_graph: Le graphe LangGraph compilé
        topic: Le sujet de la newsletter
        user_email: L'email du destinataire
        interval_hours: Intervalle en heures entre chaque envoi (défaut: 1h)
    """
    global scheduler_thread, active_topic, active_email, last_execution_time, next_execution_time

    # Arrêter tout scheduling précédent
    stop_scheduling()
    
    if not compiled_graph:
        logging.error("Impossible de démarrer le scheduler: graphe non compilé.")
        return False
        
    logging.info(f"Configuration du scheduler pour exécuter toutes les {interval_hours} heure(s).")

    # Mettre à jour les variables globales
    active_topic = topic
    active_email = user_email

    # Exécution immédiate pour la première fois
    run_graph_job(compiled_graph, topic, user_email)
    
    # Planification des exécutions suivantes
    # Convertir interval_hours en secondes pour schedule
    interval_seconds = int(interval_hours * 3600)
    schedule.every(interval_seconds).seconds.do(
        run_graph_job,
        compiled_graph=compiled_graph,
        topic=topic,
        user_email=user_email
    )

    # Démarrer la boucle du scheduler dans un thread séparé
    def scheduler_loop():
        logging.info("Démarrage de la boucle du scheduler...")
        while not stop_scheduler.is_set():
            schedule.run_pending()
            # Vérifier toutes les 10 secondes si une tâche est prête
            time.sleep(10)
        logging.info("Boucle du scheduler arrêtée.")
        schedule.clear()  # Nettoyer les tâches planifiées

    stop_scheduler.clear()  # Réinitialiser l'event d'arrêt
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    logging.info(f"Thread du scheduler démarré pour le sujet '{topic}'.")
    return True


def stop_scheduling():
    """Arrête la boucle du scheduler et nettoie les ressources."""
    global scheduler_thread, active_topic, active_email, last_execution_time, next_execution_time
    
    # Vérifier si un thread est actif
    if scheduler_thread is not None and scheduler_thread.is_alive():
        logging.info(f"Arrêt du scheduler pour le sujet '{active_topic}'.")
        stop_scheduler.set()
        
        try:
            scheduler_thread.join(timeout=5)  # Attendre 5 secondes max
            
            # Vérifier si le thread s'est bien arrêté
            if scheduler_thread.is_alive():
                logging.warning("Le thread du scheduler n'a pas pu être arrêté proprement.")
        except Exception as e:
            logging.error(f"Erreur lors de l'arrêt du thread: {e}")
        
        # Nettoyer les jobs planifiés
        schedule.clear()
        
        # Réinitialiser les variables globales
        scheduler_thread = None
        active_topic = None
        active_email = None
        last_execution_time = None
        next_execution_time = None
        
        logging.info("Scheduler arrêté et nettoyé.")
        return True
    else:
        logging.info("Aucun scheduler actif à arrêter.")
        # Assurez-vous que les variables globales sont bien nettoyées
        scheduler_thread = None
        active_topic = None
        active_email = None
        last_execution_time = None
        next_execution_time = None
        schedule.clear()
        return False


def get_active_state():
    """
    Récupère l'état actif du scheduler.
    
    Returns:
        dict: Informations sur l'état actif du scheduler
    """
    global next_execution_time  # Déplacer la déclaration globale ici, au début de la fonction
    
    is_active = scheduler_thread is not None and scheduler_thread.is_alive()
    
    result = {
        "active": is_active,
        "topic": active_topic,
        "email": active_email,
        "last_execution": None,
        "next_execution": None
    }
    
    if last_execution_time:
        result["last_execution"] = last_execution_time.isoformat()
    
    if next_execution_time:
        result["next_execution"] = next_execution_time.isoformat()
        
    # Vérifie si next_execution_time est dépassé et met à jour si nécessaire
    if is_active and next_execution_time:
        now = datetime.now(next_execution_time.tzinfo)
        if next_execution_time < now:
            # Mettre à jour pour l'heure suivante
            updated_next = now.replace(
                minute=0, 
                second=0, 
                microsecond=0,
                hour=now.hour + 1
            )
            
            if updated_next.hour >= 24:
                updated_next = updated_next.replace(hour=0, day=updated_next.day+1)
                
            next_execution_time = updated_next  # La variable globale est maintenant correctement déclarée
            result["next_execution"] = next_execution_time.isoformat()
    
    return result