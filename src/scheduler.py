# src/news_aggregator/scheduler.py
import threading
import time
import logging
from datetime import datetime, timedelta
import pytz
import signal
import traceback

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Global scheduler state
_scheduler_thread = None
_stop_event = threading.Event()
_scheduler_state = {
    "active": False,
    "topic": None,
    "user_email": None,
    "last_execution": None,
    "next_execution": None,
    "interval_hours": 24  # Default to daily updates
}

def _execute_task(graph, topic, user_email):
    """
    Execute the newsletter generation task.
    
    Args:
        graph: The compiled LangGraph
        topic: Topic to search for
        user_email: Email to send the newsletter to
    """
    # Import here to avoid circular import issues
    from src.news_aggregator.graph import GraphState
    
    try:
        logging.info(f"--- Starting scheduled execution for topic: '{topic}' at {datetime.now().strftime('%H:%M:%S')} ---")
        
        # Create input state
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz).strftime("%d/%m/%Y at %H:%M")
        
        inputs = GraphState(
            topic=topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=user_email,
            timestamp=current_time
        )
        
        # Record execution time
        _scheduler_state["last_execution"] = datetime.now().isoformat()
        
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
    logging.info(f"Starting scheduler loop...")
    
    # Execute immediately on start
    _execute_task(graph, topic, user_email)
    
    # Calculate next execution time
    next_run = datetime.now() + timedelta(hours=interval_hours)
    _scheduler_state["next_execution"] = next_run.isoformat()
    logging.info(f"Next execution scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    while not _stop_event.is_set():
        # Check if it's time to run
        now = datetime.now()
        if now >= next_run:
            # Execute the task
            _execute_task(graph, topic, user_email)
            
            # Calculate next execution time
            next_run = now + timedelta(hours=interval_hours)
            _scheduler_state["next_execution"] = next_run.isoformat()
            logging.info(f"Next execution scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Sleep for a while before checking again (60 seconds)
        for _ in range(60):
            if _stop_event.is_set():
                break
            time.sleep(1)
    
    logging.info("Scheduler loop stopped.")

def start_scheduling(graph, topic, user_email, interval_hours=24):
    """
    Start the scheduling process.
    
    Args:
        graph: The compiled LangGraph
        topic: Topic to search for
        user_email: Email to send the newsletter to
        interval_hours: Hours between executions (default: 24 for daily)
    """
    global _scheduler_thread, _stop_event, _scheduler_state
    
    # Stop any existing scheduler
    stop_scheduling()
    logging.info(f"No active scheduler to stop.")
    
    # Configure new scheduler
    logging.info(f"Configuring scheduler to run every {interval_hours} hour(s).")
    _stop_event.clear()
    _scheduler_state["active"] = True
    _scheduler_state["topic"] = topic
    _scheduler_state["user_email"] = user_email
    _scheduler_state["interval_hours"] = interval_hours
    
    # Start the scheduler thread
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(graph, topic, user_email, interval_hours),
        daemon=True  # This makes sure the thread doesn't block app shutdown
    )
    _scheduler_thread.start()
    
    logging.info(f"Scheduler thread started for topic '{topic}'.")
    return True

def stop_scheduling():
    """
    Stop the current scheduling process.
    
    Returns:
        bool: True if a scheduler was stopped, False otherwise
    """
    global _scheduler_thread, _stop_event, _scheduler_state
    
    if not _scheduler_state["active"]:
        logging.info("No active scheduler to stop.")
        return False
    
    # Signal the scheduler to stop
    logging.info(f"Stopping scheduler for topic '{_scheduler_state['topic']}'.")
    _stop_event.set()
    
    # Wait for scheduler thread to finish (with timeout)
    if _scheduler_thread and _scheduler_thread.is_alive():
        try:
            _scheduler_thread.join(timeout=5.0)
            logging.info("Scheduler loop stopped.")
        except Exception as e:
            logging.warning(f"Error waiting for scheduler thread: {e}")
    
    # Clean up
    _scheduler_thread = None
    _scheduler_state["active"] = False
    _scheduler_state["topic"] = None
    _scheduler_state["user_email"] = None
    _scheduler_state["next_execution"] = None
    
    logging.info("Scheduler stopped and cleaned up.")
    return True

def get_active_state():
    """
    Get the current scheduler state.
    
    Returns:
        dict: Current scheduler state
    """
    return _scheduler_state.copy()

# Register signal handlers for clean shutdown
def _handle_signal(signum, frame):
    logging.info(f"Received signal {signum}, stopping scheduler...")
    stop_scheduling()

# Register for common termination signals
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# For testing
if __name__ == "__main__":
    # Simple test
    from datetime import datetime
    
    # Mock graph
    class MockGraph:
        def invoke(self, inputs):
            print(f"Mock graph invoked with topic: {inputs['topic']}")
            return {"error": None}
    
    mock_graph = MockGraph()
    
    print("Starting test scheduler (5-second interval)...")
    start_scheduling(mock_graph, "Test Topic", "test@example.com", interval_hours=1/720)  # 5 seconds
    
    try:
        # Run for 15 seconds
        time.sleep(15)
    finally:
        print("Stopping test scheduler...")
        stop_scheduling()