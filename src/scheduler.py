# src/news_aggregator/scheduler.py
import threading
import time
import logging
from datetime import datetime, timedelta, timezone
import pytz # Keep pytz for timezone formatting if needed elsewhere
import signal
import traceback

# Logging configuration (English)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s')

# Global scheduler state
_scheduler_thread = None
_stop_event = threading.Event()
_scheduler_state = {
    "active": False,
    "topic": None,
    "user_email": None,
    "last_execution": None, # Store as UTC ISO string
    "next_execution": None, # Store as UTC ISO string
    "interval_hours": 24,   # Default to daily updates (24 hours)
    "status_message": "Scheduler is idle."
}
_scheduler_lock = threading.Lock() # To protect access to _scheduler_state

def _execute_task(graph, topic, user_email):
    """
    Executes the newsletter generation task.

    Args:
        graph: The compiled LangGraph object.
        topic: The topic to search for.
        user_email: The email address to send the newsletter to.
    """
    # Import here to avoid potential circular import issues if GraphState moves
    from .graph import GraphState

    task_start_time = datetime.now(timezone.utc)
    logging.info(f"--- Starting scheduled task execution for topic: '{topic}' at {task_start_time.isoformat()} ---")
    update_scheduler_status("Task execution started.")

    try:
        # Use UTC for internal logic, format for display later
        current_time_utc = datetime.now(timezone.utc)
        # Example: Format for display in Paris time if needed
        paris_tz = pytz.timezone('Europe/Paris')
        display_time = current_time_utc.astimezone(paris_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

        inputs = GraphState(
            topic=topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=user_email,
            # Pass a display-friendly timestamp if needed by the graph/email template
            timestamp=display_time
        )

        # Update last execution time *before* invoking
        with _scheduler_lock:
            _scheduler_state["last_execution"] = task_start_time.isoformat()

        # Execute the LangGraph workflow
        logging.info("Invoking LangGraph...")
        result = graph.invoke(inputs)
        logging.info("LangGraph invocation completed.")

        # Handle the result
        if result.get("error"):
            error_message = f"Error during graph execution: {result['error']}"
            logging.error(error_message)
            update_scheduler_status(f"Task failed: {result['error']}")
        else:
            success_message = "Newsletter generation and delivery task completed successfully."
            logging.info(success_message)
            update_scheduler_status("Task completed successfully.")

    except Exception as e:
        error_trace = traceback.format_exc()
        error_message = f"Unhandled exception during scheduler task execution: {str(e)}"
        logging.error(error_message)
        logging.error(f"Traceback:\n{error_trace}")
        update_scheduler_status(f"Task failed with exception: {str(e)}")

    finally:
        task_end_time = datetime.now(timezone.utc)
        duration = (task_end_time - task_start_time).total_seconds()
        logging.info(f"--- Scheduled task execution finished in {duration:.2f} seconds ---")

def _scheduler_loop(graph, topic, user_email, interval_hours):
    """
    The main loop for the scheduler thread.

    Args:
        graph: The compiled LangGraph object.
        topic: The topic to monitor.
        user_email: The recipient email address.
        interval_hours: The interval between task executions in hours.
    """
    thread_name = threading.current_thread().name
    logging.info(f"Scheduler loop started in thread '{thread_name}'. Interval: {interval_hours} hours.")
    update_scheduler_status(f"Scheduler active. Monitoring '{topic}'. Interval: {interval_hours}h.")

    try:
        # --- Execute immediately on start ---
        logging.info("Performing initial task execution immediately upon start.")
        _execute_task(graph, topic, user_email)
        logging.info("Initial task execution finished.")
        # ------------------------------------

        while not _stop_event.is_set():
            # Calculate the next run time based on the *last scheduled* start time
            # This prevents drift if tasks take a long time.
            last_exec_iso = get_active_state().get("last_execution")
            if last_exec_iso:
                last_exec_time = datetime.fromisoformat(last_exec_iso.replace('Z', '+00:00'))
            else:
                 # Should not happen after initial run, but handle defensively
                last_exec_time = datetime.now(timezone.utc)
                logging.warning("Last execution time not found, using current time for scheduling.")

            next_run_time = last_exec_time + timedelta(hours=interval_hours)

            with _scheduler_lock:
                _scheduler_state["next_execution"] = next_run_time.isoformat()

            logging.info(f"Next execution scheduled for: {next_run_time.isoformat()}")
            update_scheduler_status(f"Waiting for next execution at {next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # Wait until the next run time or stop event
            while datetime.now(timezone.utc) < next_run_time and not _stop_event.is_set():
                # Sleep in shorter intervals to be responsive to the stop event
                wait_time = min(60, (next_run_time - datetime.now(timezone.utc)).total_seconds())
                if wait_time > 0:
                    _stop_event.wait(timeout=wait_time) # More efficient than time.sleep loop

            if _stop_event.is_set():
                logging.info("Stop event detected, exiting scheduler loop.")
                break

            # It's time to run the task again
            logging.info("Scheduled time reached. Starting next task execution.")
            _execute_task(graph, topic, user_email)

    except Exception as e:
        logging.error(f"Fatal error in scheduler loop: {e}", exc_info=True)
        update_scheduler_status(f"Scheduler loop crashed: {e}")
        # Consider notifying admin or attempting recovery

    finally:
        logging.info(f"Scheduler loop finished for thread '{thread_name}'.")
        update_scheduler_status("Scheduler stopped.")
        # Ensure state is reset cleanly if the loop exits unexpectedly
        with _scheduler_lock:
            _scheduler_state["active"] = False
            # Keep topic/email for potential restart debugging? Optional.
            # _scheduler_state["topic"] = None
            # _scheduler_state["user_email"] = None
            _scheduler_state["next_execution"] = None

def start_scheduling(graph, topic, user_email, interval_hours=24):
    """
    Starts the background scheduling process.

    Args:
        graph: The compiled LangGraph object.
        topic: The topic to monitor.
        user_email: The recipient email address.
        interval_hours: The interval in hours (default: 24 for daily).

    Returns:
        bool: True if scheduling was started successfully, False otherwise.
    """
    global _scheduler_thread, _stop_event

    with _scheduler_lock:
        if _scheduler_state["active"]:
            logging.warning("Scheduler is already active. Stop it before starting a new one.")
            return False

        # Stop any potentially lingering old thread (defensive)
        if _scheduler_thread and _scheduler_thread.is_alive():
            logging.warning("Found an unexpected alive scheduler thread. Attempting to stop it.")
            _stop_event.set()
            _scheduler_thread.join(timeout=5.0)
            if _scheduler_thread.is_alive():
                logging.error("Failed to stop lingering scheduler thread!")
                # Decide how to handle this - maybe prevent starting a new one?
                return False # Prevent starting a new one if old one can't be stopped

        logging.info(f"Attempting to start scheduler for topic '{topic}' with interval {interval_hours} hours.")

        # Reset stop event and update state
        _stop_event.clear()
        _scheduler_state.update({
            "active": True,
            "topic": topic,
            "user_email": user_email,
            "interval_hours": interval_hours,
            "last_execution": None, # Reset last execution
            "next_execution": None, # Will be set by the loop
            "status_message": "Scheduler starting..."
        })

        # Create and start the new scheduler thread
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(graph, topic, user_email, interval_hours),
            daemon=True, # Allows the main program to exit even if this thread is running
            name=f"SchedulerThread-{topic[:10]}" # Give the thread a name
        )
        _scheduler_thread.start()

        logging.info(f"Scheduler thread '{_scheduler_thread.name}' started successfully.")
        return True

def stop_scheduling():
    """
    Stops the current scheduling process gracefully.

    Returns:
        bool: True if a scheduler was active and signaled to stop, False otherwise.
    """
    global _scheduler_thread

    with _scheduler_lock:
        if not _scheduler_state["active"]:
            logging.info("No active scheduler to stop.")
            return False

        logging.info(f"Attempting to stop scheduler for topic '{_scheduler_state['topic']}'.")
        update_scheduler_status("Scheduler stopping...")

        # Signal the loop to stop
        _stop_event.set()

    # Wait for the thread to finish outside the lock to avoid deadlocks
    if _scheduler_thread and _scheduler_thread.is_alive():
        logging.info(f"Waiting for scheduler thread '{_scheduler_thread.name}' to join...")
        _scheduler_thread.join(timeout=10.0) # Increased timeout

        if _scheduler_thread.is_alive():
            logging.warning(f"Scheduler thread '{_scheduler_thread.name}' did not stop within the timeout.")
            # Consider logging this as an error or potential issue
        else:
            logging.info(f"Scheduler thread '{_scheduler_thread.name}' joined successfully.")
    else:
        logging.info("Scheduler thread was not found or already stopped.")


    # Clean up state variables (might be partially done by loop exit)
    with _scheduler_lock:
        _scheduler_state.update({
            "active": False,
            "topic": None,
            "user_email": None,
            "next_execution": None,
            # Keep last_execution for historical info? Optional.
             # "last_execution": None,
            "status_message": "Scheduler stopped."
        })
        _scheduler_thread = None # Clear the thread reference

    logging.info("Scheduler stopped and state cleaned up.")
    return True


def get_active_state():
    """
    Returns a copy of the current scheduler state in a thread-safe manner.

    Returns:
        dict: A copy of the current scheduler state.
    """
    with _scheduler_lock:
        # Return a copy to prevent external modification of the internal state
        return _scheduler_state.copy()

def update_scheduler_status(message: str):
    """Updates the status message in the scheduler state."""
    with _scheduler_lock:
        _scheduler_state["status_message"] = message
    logging.debug(f"Scheduler status updated: {message}")


# Graceful shutdown handling
def _handle_signal(signum, frame):
    """Signal handler for SIGINT and SIGTERM."""
    logging.warning(f"Received signal {signal.Signals(signum).name}. Initiating graceful shutdown...")
    stop_scheduling()
    # Optionally, add a small delay or exit logic if needed
    logging.info("Shutdown process initiated. Exiting signal handler.")
    # Depending on the environment, you might need sys.exit here,
    # but often letting the main thread finish is cleaner.
    # sys.exit(0)

# Register signal handlers
try:
    signal.signal(signal.SIGINT, _handle_signal)  # Ctrl+C
    signal.signal(signal.SIGTERM, _handle_signal) # Kill signal
    logging.info("Registered signal handlers for SIGINT and SIGTERM.")
except ValueError:
    logging.warning("Could not register signal handlers (might be running in an environment like Windows without full signal support).")


# Example for standalone testing
if __name__ == "__main__":
    print("--- Scheduler Standalone Test ---")

    # Mock Graph for testing
    class MockGraph:
        def invoke(self, inputs):
            print(f"[{datetime.now(timezone.utc).isoformat()}] MockGraph invoked for topic: {inputs['topic']}")
            # Simulate work
            time.sleep(2)
            print(f"[{datetime.now(timezone.utc).isoformat()}] MockGraph finished for topic: {inputs['topic']}")
            # Simulate potential error
            # import random
            # if random.random() < 0.1:
            #     return {"error": "Simulated random error"}
            return {"error": None}

    mock_graph = MockGraph()
    test_topic = "Test Topic"
    test_email = "test@example.com"
    test_interval_seconds = 5 # Use a short interval for testing
    test_interval_hours = test_interval_seconds / 3600.0

    print(f"Starting test scheduler for '{test_topic}'. Interval: {test_interval_seconds} seconds.")
    if start_scheduling(mock_graph, test_topic, test_email, interval_hours=test_interval_hours):
        print("Scheduler started successfully.")
    else:
        print("Failed to start scheduler.")
        exit(1)

    try:
        # Keep the main thread alive to observe the scheduler
        run_duration = 20 # seconds
        print(f"Running test for {run_duration} seconds. Press Ctrl+C to stop earlier.")
        for i in range(run_duration):
             current_state = get_active_state()
             print(f"[{datetime.now(timezone.utc).time()}] State: Active={current_state['active']}, "
                   f"Next: {current_state.get('next_execution', 'N/A')}, "
                   f"Status: {current_state.get('status_message', 'N/A')}")
             time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C detected.")
    finally:
        print("Initiating scheduler stop...")
        if stop_scheduling():
            print("Stop signal sent successfully.")
        else:
            print("Scheduler was not active or already stopped.")
        print("Waiting for scheduler thread to exit completely...")
        # Give it a moment to ensure logs are flushed, etc.
        time.sleep(2)
        print("--- Scheduler Standalone Test Finished ---")