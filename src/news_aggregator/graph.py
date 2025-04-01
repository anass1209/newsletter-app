import logging
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
import google.generativeai as genai
from . import config
from .utils import send_email
from datetime import datetime
import pytz
import time
import asyncio

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Graph state definition
class GraphState(TypedDict):
    topic: str
    tavily_results: List[Dict[str, Any]]
    structured_summary: str
    html_content: str
    error: str | None
    user_email: str
    timestamp: str

# Graph nodes
def fetch_tavily_data(state: GraphState) -> GraphState:
    """Fetch recent data from Tavily API with timeout handling."""
    topic = state['topic']
    logging.info(f"Fetching advanced search for: {topic}")
    
    paris_tz = pytz.timezone('Europe/Paris')
    current_time = datetime.now(paris_tz).strftime("%d/%m/%Y at %H:%M")
    
    if not config.TAVILY_API_KEY:
        logging.error("Tavily API key not configured.")
        return {**state, "error": "Tavily API key not configured.", "timestamp": current_time}

    try:
        # Log API key status (but not the key itself)
        logging.info(f"Using Tavily API key (length: {len(config.TAVILY_API_KEY)})")
        
        # Initialize client with timeout
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        # Create a specific search query for recent content
        search_query = f"Latest news, research papers, developments, announcements, and breakthroughs about {topic} in the last 24 hours"
        
        # Start timer for performance monitoring
        start_time = time.time()
        
        # Execute search with parameters optimized for recent content
        response = tavily.search(
            query=search_query,
            search_depth="advanced",
            max_results=15,
            include_raw_content=True,
            include_domains=["scholar.google.com", "arxiv.org", "github.com", "medium.com", "news.google.com"],
            include_answer=False,
            search_timedelta_days=3  # Look back 3 days maximum
        )
        
        # Log performance
        elapsed_time = time.time() - start_time
        logging.info(f"Tavily search completed in {elapsed_time:.2f} seconds")

        # Process and filter results
        results = response.get('results', [])
        unique_results = []
        seen_urls = set()
        seen_titles = set()
        
        for result in results:
            url = result.get('url')
            title = result.get('title', '').lower()
            # Filter out duplicate or low-quality content
            if url and url not in seen_urls and not any(t in title for t in seen_titles if len(t) > 20):
                content = result.get('content', '')
                if len(content) > 100:  # Ensure content has substance
                    # Add published date check for recent content
                    published_date = result.get('published_date')
                    if published_date:
                        result['published_date_formatted'] = published_date
                    unique_results.append(result)
                    seen_urls.add(url)
                    seen_titles.add(title)

        logging.info(f"Tavily returned {len(unique_results)} unique results.")
        return {**state, "tavily_results": unique_results, "error": None, "timestamp": current_time}
    except Exception as e:
        logging.error(f"Tavily API call failed: {e}")
        return {**state, "error": f"Tavily error: {e}", "timestamp": current_time}

def summarize_with_gemini(state: GraphState) -> GraphState:
    """Generate a structured summary using Gemini with improved prompting."""
    logging.info("Generating summary with Gemini")
    if state.get("error"):
        return state
    if not config.GEMINI_API_KEY:
        logging.error("Gemini API key not configured.")
        return {**state, "error": "Gemini API key not configured."}
    if not state.get('tavily_results'):
        no_result_message = f"No recent news found for '{state['topic']}' in the last 24 hours."
        return {**state, "structured_summary": no_result_message, "html_content": f"<p>{no_result_message}</p>", "error": None}

    try:
        # Log API key status (but not the key itself)
        logging.info(f"Using Gemini API key (length: {len(config.GEMINI_API_KEY)})")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Start timer for performance monitoring
        start_time = time.time()
        
        # Format context with emphasis on recent content
        context = "\n---\n".join(
            f"Source {i+1}:\n  Title: {r.get('title', 'N/A')}\n  URL: {r.get('url', 'N/A')}\n  Date: {r.get('published_date_formatted', 'N/A')}\n  Content: {r.get('content', 'N/A')}"
            for i, r in enumerate(state['tavily_results'])
        )

        # Improved prompt that focuses on recent content
        prompt = f"""
        Topic: {state['topic']}
        Sources:
        --- START OF SOURCES ---
        {context}
        --- END OF SOURCES ---
        Instructions:
        1. Analyze the sources to identify news and developments on "{state['topic']}" FROM THE LAST 24 HOURS ONLY.
        2. Generate a structured summary IN ENGLISH:
           - Introduction with main news highlights from the last day
           - 3-5 sections, each with a bold catchy title
           - Cite sources (URL) in parentheses
           - Only include content from the last day or at most the last 3 days if not enough recent content
        3. Keep it informative, accessible, engaging, and concise.
        4. If no recent info from the last day, clearly state it and suggest related topics.
        5. Provide a general newsletter title.
        Format in Markdown.
        """
        
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.4))
        
        # Log performance
        elapsed_time = time.time() - start_time
        logging.info(f"Gemini summary generation completed in {elapsed_time:.2f} seconds")
        
        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if hasattr(response, 'prompt_feedback') else "Unknown"
            logging.error(f"Gemini response blocked: {block_reason}")
            return {**state, "error": f"Gemini error: Response blocked (Reason: {block_reason})."}

        summary = response.text
        
        # Generate HTML version with improved styling
        html_prompt = f"""
        Convert this Markdown summary to elegant HTML for email:
        {summary}
        Instructions:
        1. Retain all content and structure.
        2. Use inline CSS for email compatibility (blue palette, responsive design).
        3. Include a simple header with the newsletter title and today's date.
        4. Add clear section dividers and proper spacing.
        5. Make links open in new tabs.
        6. Include a simple footer with copyright and unsubscribe placeholder.
        """
        html_response = model.generate_content(html_prompt)
        html_content = html_response.text if html_response.parts else summary
        html_content = html_content.strip().replace("```html", "").replace("```", "")
        
        # Add analytics pixel placeholder if needed
        if "<body" in html_content and not "tracking-pixel" in html_content:
            html_content = html_content.replace("</body>", '<img src="tracking-pixel" width="1" height="1" style="display:none">\n</body>')
        
        return {**state, "structured_summary": summary, "html_content": html_content, "error": None}
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return {**state, "error": f"Gemini error: {str(e)}"}

def send_email_node(state: GraphState) -> GraphState:
    """Send the summary as an HTML email with error handling."""
    logging.info("Preparing email dispatch")
    if state.get("error"):
        logging.warning(f"Error detected, skipping email: {state['error']}")
        return state

    # Create a more descriptive subject line
    subject = f"Daily Newsletter: {state['topic']} - News from {state['timestamp']}"
    html_body = state.get('html_content', f"<h1>News on {state['topic']}</h1><p>{state['structured_summary']}</p>")
    
    # Ensure the HTML email has proper structure
    if "<html" not in html_body:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Newsletter: {state['topic']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #3498db; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .content {{ padding: 20px; background-color: #f9f9f9; border: 1px solid #ddd; }}
                .footer {{ text-align: center; font-size: 0.8em; color: #666; padding: 10px; border-top: 1px solid #ddd; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .unsubscribe {{ font-size: 0.75em; color: #999; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="header"><h1>Daily News: {state['topic']}</h1><p>Updated on {state['timestamp']}</p></div>
            <div class="content">{html_body}</div>
            <div class="footer">
                <p>Automated newsletter for daily updates on {state['topic']}.</p>
                <p>© 2025 - Newsletter Monitor</p>
                <p class="unsubscribe">To unsubscribe, visit the <a href="#">settings page</a>.</p>
            </div>
        </body>
        </html>
        """

    recipient = state.get("user_email")
    if not recipient:
        logging.error("Recipient email missing.")
        return {**state, "error": "Recipient email missing."}

    # Try multiple times with exponential backoff
    max_attempts = 3
    success = False
    for attempt in range(1, max_attempts + 1):
        logging.info(f"Email sending attempt {attempt}/{max_attempts}")
        success = send_email(recipient_email=recipient, subject=subject, body=state['structured_summary'], html_body=html_body)
        if success:
            logging.info(f"Email successfully sent to {recipient} on attempt {attempt}")
            break
        elif attempt < max_attempts:
            # Exponential backoff
            wait_time = 2 ** attempt
            logging.warning(f"Email sending failed, retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    if not success:
        return {**state, "error": "Email sending failed after multiple attempts."}
    return state

# Graph construction
def build_graph() -> StateGraph:
    """Build and return the LangGraph StateGraph."""
    workflow = StateGraph(GraphState)
    workflow.add_node("fetch_data", fetch_tavily_data)
    workflow.add_node("summarize", summarize_with_gemini)
    workflow.add_node("send_notification", send_email_node)
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "summarize")
    workflow.add_edge("summarize", "send_notification")
    workflow.add_edge("send_notification", END)
    app = workflow.compile()
    logging.info("LangGraph compiled successfully.")
    return app

if __name__ == '__main__':
    if config.load_credentials_from_env():
        config.USER_EMAIL = "test@example.com"
        test_graph = build_graph()
        inputs = GraphState(
            topic="Artificial Intelligence",
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=config.USER_EMAIL,
            timestamp=""
        )
        print("\n--- Graph Execution (Test) ---")
        results = test_graph.invoke(inputs)
        print("\n--- Final Graph State (Test) ---")
        from pprint import pprint
        pprint(results)
        if results.get('error'):
            print(f"\nERROR DETECTED (Test): {results['error']}")
        else:
            print("\n--- Generated Summary (Test) ---")
            print(results.get('structured_summary', 'No summary available.'))
    else:
        print("Configure API keys and email in .env to test the graph.")