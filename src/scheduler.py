# src/news_aggregator/scheduler.py
import threading
import time
import logging
from datetime import datetime, timedelta, timezone # Utiliser timezone de datetime (Python 3.2+)
import pytz # Toujours nécessaire pour les fuseaux horaires spécifiques comme Paris
import signal
import traceback

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# --- Avertissement important concernant les Workers Multiples ---
# Si cette application est déployée avec plusieurs workers web (ex: Gunicorn avec WEB_CONCURRENCY > 1),
# chaque worker lancera son propre thread de scheduler, entraînant des exécutions multiples (ex: emails dupliqués).
# Pour une planification fiable dans un tel environnement, utilisez une solution comme :
# 1. L'add-on Heroku Scheduler (recommandé sur Heroku) pour lancer une tâche ponctuelle.
# 2. Un type de processus 'worker' dédié dans votre Procfile, mis à l'échelle à 1 dyno.
# 3. Un système de verrouillage distribué (plus complexe).
# Le code ci-dessous suppose qu'il s'exécute dans un contexte de processus unique pour la planification.
# --------------------------------------------------------------

# Global scheduler state
_scheduler_thread = None
_stop_event = threading.Event()
_scheduler_state = {
    "active": False,
    "topic": None,
    "user_email": None,
    "last_execution": None, # Stocké en UTC ISO format
    "next_execution": None, # Stocké en UTC ISO format
    "interval_hours": 24  # Default to daily updates
}

# Définir UTC pour la cohérence
UTC = timezone.utc

def _execute_task(graph, topic, user_email):
    """
    Execute the newsletter generation task.

    Args:
        graph: The compiled LangGraph
        topic: Topic to search for
        user_email: Email to send the newsletter to
    """
    # Import here to avoid circular import issues and ensure latest code if workers reload
    from src.news_aggregator.graph import GraphState # Assurez-vous que ce chemin est correct

    try:
        # Utiliser l'heure UTC pour le log de début interne
        start_time_utc = datetime.now(UTC)
        logging.info(f"--- Starting scheduled execution for topic: '{topic}' at {start_time_utc.strftime('%Y-%m-%d %H:%M:%S %Z')} ---")

        # Create input state
        # Utiliser un fuseau horaire spécifique pour l'affichage si nécessaire
        paris_tz = pytz.timezone('Europe/Paris')
        current_time_paris = datetime.now(paris_tz).strftime("%d/%m/%Y at %H:%M")

        inputs = GraphState(
            topic=topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=user_email,
            timestamp=current_time_paris # Horodatage pour l'utilisateur
        )

        # Record execution time (using UTC)
        # Utiliser now(UTC) pour une date/heure aware
        _scheduler_state["last_execution"] = datetime.now(UTC).isoformat()

        # Execute graph
        result = graph.invoke(inputs)

        # Handle result
        if result.get("error"):
            logging.error(f"Error during graph execution: {result['error']}")
        else:
            logging.info("Newsletter generation and delivery completed successfully")

    except Exception as e:
        error_trace = traceback.format_exc()
        logging.error(f"Scheduler task execution error: {str(e)}")
        logging.error(f"Traceback: {error_trace}")

def _scheduler_loop(graph, topic, user_email, interval_hours):
    """
    Main scheduler loop function.

    Args:
        graph: The compiled LangGraph
        topic: Topic to search for
        user_email: Email to send the newsletter to
        interval_hours: Hours between executions
    """
    logging.info(f"Starting scheduler loop for topic '{topic}'...")

    # --- Initial Execution ---
    # Vérifier si on doit arrêter avant même la première exécution
    if _stop_event.is_set():
        logging.info("Stop event set before first execution. Exiting scheduler loop.")
        return
    _execute_task(graph, topic, user_email)

    # --- Scheduling Logic ---
    while not _stop_event.is_set():
        try:
            # Calculate next execution time using aware UTC datetime
            now_utc = datetime.now(UTC)
            # Assurer que last_execution est aware pour le calcul (au cas où il viendrait d'un état ancien/invalide)
            # Si _scheduler_state["last_execution"] est None ou invalide, on se base sur now_utc
            last_exec_time = now_utc
            if _scheduler_state["last_execution"]:
                try:
                    last_exec_time = datetime.fromisoformat(_scheduler_state["last_execution"].replace('Z', '+00:00'))
                    # S'assurer qu'il est aware
                    if last_exec_time.tzinfo is None:
                         last_exec_time = last_exec_time.replace(tzinfo=UTC) # Suppose UTC si naive
                except ValueError:
                     logging.warning(f"Could not parse last_execution time '{_scheduler_state['last_execution']}', using current time for scheduling.")
                     last_exec_time = now_utc # Fallback

            next_run_utc = last_exec_time + timedelta(hours=interval_hours)
            _scheduler_state["next_execution"] = next_run_utc.isoformat()
            logging.info(f"Next execution scheduled for: {next_run_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            # --- Wait until next execution ---
            while datetime.now(UTC) < next_run_utc and not _stop_event.is_set():
                # Calculate remaining time, sleep for shorter intervals
                # Check every 10 seconds for the stop event
                wait_time = min(10, (next_run_utc - datetime.now(UTC)).total_seconds())
                if wait_time > 0:
                    # time.sleep can be interrupted by signals, which is fine
                    time.sleep(wait_time)

            # Check if we woke up because it's time or because we should stop
            if _stop_event.is_set():
                break # Exit the main while loop

            # --- Time to Execute ---
            if datetime.now(UTC) >= next_run_utc:
                 # Double check stop event right before execution
                if _stop_event.is_set():
                    logging.info("Stop event set just before task execution.")
                    break
                _execute_task(graph, topic, user_email)
                # La prochaine exécution sera calculée au début de la boucle suivante

        except Exception as e:
            logging.error(f"Error in scheduler loop itself: {e}", exc_info=True)
            # Avoid busy-looping on error; wait a bit before retrying loop logic
            if not _stop_event.wait(60): # Attendre 60s ou jusqu'à l'arrêt
                pass # Continue la boucle si non arrêté

    logging.info(f"Scheduler loop stopped for topic '{_scheduler_state.get('topic', 'N/A')}'.")


def start_scheduling(graph, topic, user_email, interval_hours=24):
    """
    Start the scheduling process. Ensures only one scheduler runs at a time (within this process).

    Args:
        graph: The compiled LangGraph
        topic: Topic to search for
        user_email: Email to send the newsletter to
        interval_hours: Hours between executions (default: 24 for daily)
    """
    global _scheduler_thread, _stop_event, _scheduler_state

    # Stop any existing scheduler first
    if _scheduler_state["active"]:
        logging.info("Stopping existing scheduler before starting a new one.")
        if not stop_scheduling():
             logging.warning("Failed to stop the existing scheduler cleanly.")
             # Decide if you want to proceed anyway or return False
    # else: # Log retiré car stop_scheduling logge déjà s'il n'y a rien à faire
        # logging.info("No active scheduler found, proceeding to start.")
        # pass

    # Configure new scheduler state immediately after ensuring stop
    logging.info(f"Configuring scheduler for topic '{topic}' to run every {interval_hours} hour(s).")
    _stop_event.clear() # Reset the stop event for the new thread
    _scheduler_state["active"] = True
    _scheduler_state["topic"] = topic
    _scheduler_state["user_email"] = user_email
    _scheduler_state["interval_hours"] = interval_hours
    _scheduler_state["last_execution"] = None # Reset last execution time
    _scheduler_state["next_execution"] = None # Reset next execution time

    # Start the scheduler thread
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(graph, topic, user_email, interval_hours),
        daemon=True  # Allows app exit even if this thread is running
    )
    _scheduler_thread.start()

    logging.info(f"Scheduler thread started successfully for topic '{topic}'.")
    return True

def stop_scheduling():
    """
    Stop the current scheduling process.

    Returns:
        bool: True if a scheduler was active and signaled to stop, False otherwise.
              Note: Doesn't guarantee the thread has terminated, only that the signal was sent.
    """
    global _scheduler_thread, _stop_event, _scheduler_state

    if not _scheduler_state.get("active", False):
        logging.info("No active scheduler to stop.")
        return False # Indicate nothing was running

    current_topic = _scheduler_state.get('topic', 'N/A')
    logging.info(f"Attempting to stop scheduler for topic '{current_topic}'.")

    # 1. Signal the thread to stop
    _stop_event.set()

    # 2. Wait briefly for the thread to exit (optional but good practice)
    thread_to_join = _scheduler_thread # Capture the ref before clearing
    if thread_to_join and thread_to_join.is_alive():
        logging.info(f"Waiting up to 5 seconds for scheduler thread ({current_topic}) to join...")
        thread_to_join.join(timeout=5.0)
        if thread_to_join.is_alive():
            logging.warning(f"Scheduler thread ({current_topic}) did not exit within the timeout.")
        else:
            logging.info(f"Scheduler thread ({current_topic}) joined successfully.")

    # 3. Clean up global state *after* signaling and attempting join
    _scheduler_thread = None # Clear the thread reference
    _scheduler_state["active"] = False
    _scheduler_state["topic"] = None
    _scheduler_state["user_email"] = None
    # Keep last_execution ? Maybe useful for display even after stop? Optional.
    # _scheduler_state["last_execution"] = None
    _scheduler_state["next_execution"] = None
    # _stop_event is kept, just set. Will be cleared on next start.

    logging.info(f"Scheduler stop signal sent and state cleaned up for topic '{current_topic}'.")
    return True # Indicate that a stop was attempted on an active scheduler


def get_active_state():
    """
    Get the current scheduler state. Returns a copy.

    Returns:
        dict: Current scheduler state
    """
    # Ensure thread-safety if state updates become more complex,
    # but for simple reads/writes from one thread and reads from others,
    # a simple copy is usually sufficient given Python's GIL.
    # A lock could be added around state modifications and reads if needed.
    return _scheduler_state.copy()

# Register signal handlers for clean shutdown
def _handle_signal(signum, frame):
    signal_name = signal.Signals(signum).name
    logging.info(f"Received signal {signal_name} ({signum}), stopping scheduler...")
    if _scheduler_state.get("active"):
        stop_scheduling()
    else:
        logging.info("Scheduler was not active when signal was received.")
    # You might want to exit the application here too, depending on context
    # import sys
    # sys.exit(0)

# Register for common termination signals
# SIGINT is typically Ctrl+C
signal.signal(signal.SIGINT, _handle_signal)
# SIGTERM is sent by Heroku/Docker/etc. for graceful shutdown
signal.signal(signal.SIGTERM, _handle_signal)

# For testing
if __name__ == "__main__":
    # Simple test
    from datetime import datetime

    # Mock graph
    class MockGraph:
        def invoke(self, inputs):
            print(f"[{datetime.now(UTC).isoformat()}] Mock graph invoked with topic: {inputs['topic']}")
            # Simulate work
            time.sleep(2)
            print(f"[{datetime.now(UTC).isoformat()}] Mock graph finished for topic: {inputs['topic']}")
            return {"error": None}

    mock_graph = MockGraph()

    print("Starting test scheduler (10-second interval)...")
    # Use a more realistic interval for testing sleeps
    start_scheduling(mock_graph, "Test Topic", "test@example.com", interval_hours=10/3600) # 10 seconds

    try:
        # Run indefinitely until Ctrl+C
        print("Scheduler running. Press Ctrl+C to stop.")
        while True:
            current_state = get_active_state()
            # print(f"Current State: {current_state}") # Optional: print state periodically
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nCtrl+C detected.")
    finally:
        print("Stopping test scheduler via finally block (should already be stopped by signal handler)...")
        # Signal handler should have already called stop_scheduling
        if _scheduler_state.get("active"):
             stop_scheduling() # Call again just in case signal wasn't caught?
        print("Scheduler test finished.")