import logging
import re
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
import google.generativeai as genai
from . import config
from .utils import send_email
from datetime import datetime
import pytz

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
    """Fetch recent data from Tavily API."""
    topic = state['topic']
    logging.info(f"Fetching advanced search for: {topic}")
    
    current_time = datetime.now(pytz.UTC).strftime("%d/%m/%Y at %H:%M")

    # Reload configuration to ensure we have latest API keys
    from . import config
    if not config.TAVILY_API_KEY:
        logging.error("Tavily API key not configured.")
        return {**state, "error": "Tavily API key not configured.", "timestamp": current_time}

    try:
        # Log the key to debug (mask most of it for security)
        key_part = config.TAVILY_API_KEY[:4] + "..." if config.TAVILY_API_KEY else "None"
        logging.info(f"Using Tavily API key starting with: {key_part}")
        
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        search_query = f"Latest news, research papers, developments, announcements, and breakthroughs about {topic} in the last few days"
        response = tavily.search(
            query=search_query,
            search_depth="advanced",
            max_results=15,
            include_raw_content=True,
            include_domains=["scholar.google.com", "arxiv.org", "github.com", "medium.com", "news.google.com"],
            include_answer=False,
            search_timedelta_days=7
        )

        results = response.get('results', [])
        unique_results = []
        seen_urls = set()
        seen_titles = set()
        
        for result in results:
            url = result.get('url')
            title = result.get('title', '').lower()
            if url and url not in seen_urls and not any(t in title for t in seen_titles if len(t) > 20):
                content = result.get('content', '')
                if len(content) > 100:
                    unique_results.append(result)
                    seen_urls.add(url)
                    seen_titles.add(title)

        logging.info(f"Tavily returned {len(unique_results)} unique results.")
        return {**state, "tavily_results": unique_results, "error": None, "timestamp": current_time}
    except Exception as e:
        logging.error(f"Tavily API call failed: {e}")
        return {**state, "error": f"Tavily error: {e}", "timestamp": current_time}


def summarize_with_gemini(state: GraphState) -> GraphState:
    """Generate a structured summary using Gemini."""
    logging.info("Generating summary with Gemini")
    if state.get("error"):
        return state
    if not config.GEMINI_API_KEY:
        logging.error("Gemini API key not configured.")
        return {**state, "error": "Gemini API key not configured."}
    if not state.get('tavily_results'):
        no_result_message = f"No recent news found for '{state['topic']}' in the last search."
        return {**state, "structured_summary": no_result_message, "html_content": f"<p>{no_result_message}</p>", "error": None}

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        context = "\n---\n".join(
            f"Source {i+1}:\n  Title: {r.get('title', 'N/A')}\n  URL: {r.get('url', 'N/A')}\n  Date: {r.get('published_date', 'N/A')}\n  Content: {r.get('content', 'N/A')}"
            for i, r in enumerate(state['tavily_results'])
        )

        prompt = f"""
        Topic: {state['topic']}
        Sources:
        --- START OF SOURCES ---
        {context}
        --- END OF SOURCES ---
        Instructions:
        1. Analyze the sources to identify recent news and key developments on "{state['topic']}".
        2. Generate a structured summary IN ENGLISH:
           - Introduction with main news highlights (Start with a compelling hook)
           - 3-5 sections, each with a bold catchy title
           - Include direct quotes when relevant (in blockquote format)
           - Cite sources (URL) in parentheses
           - End with a brief conclusion or future outlook
        3. Keep it informative, accessible, engaging, and concise.
        4. If no recent info, state it and suggest related topics.
        5. Provide a compelling newsletter title.
        Format in Markdown.
        """
        
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.4))
        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if hasattr(response, 'prompt_feedback') else "Unknown"
            logging.error(f"Gemini response blocked: {block_reason}")
            return {**state, "error": f"Gemini error: Response blocked (Reason: {block_reason})."}

        summary = response.text
        
        html_prompt = f"""
        Convert this Markdown summary to elegant, modern HTML for a professional email newsletter:
        
        {summary}
        
        Instructions:
        1. Create rich, well-structured HTML with:
           - Clean, modern design elements
           - Proper article sections with headers
           - Blockquotes for direct quotes
           - Visual hierarchy with proper heading levels
           - Source citations as styled links
           
        2. Add these enhanced features:
           - Format any URLs as proper HTML links
           - For blockquotes, use elegant styling
           - Ensure good whitespace and readability
           - Add subtle dividers between sections
           - Bold or highlight key points/statistics
           - Format lists properly with spacing
           
        3. Very Important: DO NOT include <html>, <head>, <body> tags or any CSS - just the structured content HTML.
        
        4. Make it look professional and engaging for a newsletter that will appear in a CV/portfolio.
        """
        
        html_response = model.generate_content(html_prompt)
        html_content = html_response.text if html_response.parts else summary
        
        # Clean up the HTML response
        html_content = html_content.strip()
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()
        
        # Remove any full HTML document structure if present
        html_content = re.sub(r'<!DOCTYPE.*?>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<html.*?>.*?<body.*?>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'</body>.*?</html>', '', html_content, flags=re.DOTALL)
        
        return {**state, "structured_summary": summary, "html_content": html_content, "error": None}
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return {**state, "error": f"Gemini error: {str(e)}"}

# Import the new email template function
from .email_template import create_enhanced_email_template

def send_email_node(state: GraphState) -> GraphState:
    """Send the summary as an HTML email."""
    logging.info("Preparing email dispatch")
    if state.get("error"):
        logging.warning(f"Error detected, skipping email: {state['error']}")
        return state

    subject = f"Newsletter: {state['topic']} - Updates {state['timestamp']}"
    
    # Get the HTML content or fallback to structured summary if no HTML available
    html_body = state.get('html_content', '')
    
    # If no HTML was generated, format the structured summary as simple HTML
    if not html_body:
        html_body = f"<h1>News on {state['topic']}</h1><div>{state['structured_summary']}</div>"
    
    # Create enhanced email template
    enhanced_email_html = create_enhanced_email_template(
        topic=state['topic'],
        content=html_body,
        timestamp=state['timestamp']
    )
    
    recipient = state.get("user_email")
    if not recipient:
        logging.error("Recipient email missing.")
        return {**state, "error": "Recipient email missing."}

    # Send email with the enhanced template
    success = send_email(
        recipient_email=recipient, 
        subject=subject, 
        body=state['structured_summary'],  # Plain text fallback
        html_body=enhanced_email_html
    )
    
    if not success:
        return {**state, "error": "Email sending failed."}
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
            timestamp=datetime.now(pytz.UTC).strftime("%d/%m/%Y at %H:%M")
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