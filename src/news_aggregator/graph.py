# src/news_aggregator/graph.py

import logging
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
import google.generativeai as genai
from datetime import datetime, timezone
import pytz # For timezone display formatting if needed

# Import config and utils using relative paths
from . import config
from .utils import send_email, format_error_message

# Logging setup (English)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s')
log = logging.getLogger(__name__)

# --- Graph State Definition ---
class GraphState(TypedDict):
    """Defines the structure of the data passed between graph nodes."""
    topic: str                      # The user-provided topic
    tavily_results: List[Dict[str, Any]] # Results from Tavily search
    structured_summary: str         # Markdown summary from Gemini
    html_content: str               # HTML formatted summary for email
    error: str | None               # Stores error messages if any step fails
    user_email: str                 # Recipient email address
    timestamp: str                  # Timestamp for when the process started (display friendly)

# --- Graph Nodes ---

def fetch_tavily_data(state: GraphState) -> GraphState:
    """
    Node to fetch recent news and data related to the topic using the Tavily API.
    """
    topic = state.get('topic', 'Unknown Topic')
    current_time_str = state.get('timestamp', datetime.now(timezone.utc).isoformat()) # Use provided or generate UTC
    log.info(f"Node 'fetch_tavily_data': Starting search for topic '{topic}' at {current_time_str}")

    if not config.TAVILY_API_KEY:
        error_msg = "Tavily API key is not configured. Cannot perform search."
        log.error(error_msg)
        return {**state, "error": error_msg}

    try:
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        # Refined query for recent, relevant info
        search_query = (
            f"Recent news, research papers (arXiv, Google Scholar), technical articles (Medium), "
            f"project updates (GitHub), and significant announcements about '{topic}' "
            f"published within the last 7 days."
        )
        log.debug(f"Tavily Query: {search_query}")

        response = tavily.search(
            query=search_query,
            search_depth="advanced",    # Use advanced for more thorough search
            max_results=10,             # Limit results to keep summary concise
            include_raw_content=False,  # Fetch raw content only if Gemini needs it (often title/snippet is enough)
            include_domains=[           # Focus on relevant domains
                "arxiv.org", "news.google.com", "techcrunch.com", "venturebeat.com",
                 "wired.com", "zdnet.com", "github.com", "medium.com", "reuters.com", "apnews.com"
                 # Add more relevant domains as needed
                 ],
            # include_answer=False,       # We want summaries of sources, not a direct answer
            # time_delta={'days': 7} # Specify time window (alternative to using 'recent' in query)
            # Deprecated search_timedelta_days, use time_delta instead if needed explicitly
        )

        raw_results = response.get('results', [])
        log.info(f"Tavily API returned {len(raw_results)} raw results.")

        # Filter and select relevant results (Example: ensure URL and title exist)
        filtered_results = [
            res for res in raw_results
            if res.get('url') and res.get('title') # Basic filtering
            # Add more filtering if needed, e.g., based on score, content length
        ]

        # Optional: Deduplicate based on URL or title similarity if needed
        # unique_results = ...

        log.info(f"Filtered down to {len(filtered_results)} results for summarization.")
        return {**state, "tavily_results": filtered_results, "error": None}

    except Exception as e:
        error_msg = f"Tavily API call failed: {e}"
        log.exception(error_msg) # Log full traceback
        return {**state, "error": format_error_message(f"Tavily Search Error: {e}")}


def summarize_with_gemini(state: GraphState) -> GraphState:
    """
    Node to generate a structured summary of the fetched data using Google Gemini.
    Also generates an HTML version.
    """
    log.info("Node 'summarize_with_gemini': Starting content summarization.")
    # --- Pre-checks ---
    if state.get("error"):
        log.warning("Skipping summarization due to previous error.")
        return state # Pass error through

    if not config.GEMINI_API_KEY:
        error_msg = "Gemini API key is not configured. Cannot generate summary."
        log.error(error_msg)
        return {**state, "error": error_msg}

    tavily_results = state.get('tavily_results', [])
    if not tavily_results:
        topic = state.get('topic', 'the requested topic')
        no_results_msg = f"No significant new information found for '{topic}' in the recent search."
        log.info(no_results_msg)
        # Return a state indicating no news, suitable for email
        return {**state,
                "structured_summary": no_results_msg,
                "html_content": f"<p>{no_results_msg}</p>",
                "error": None} # Not an error, just no news

    # --- Prepare Context for Gemini ---
    try:
        context_parts = []
        for i, r in enumerate(tavily_results):
            title = r.get('title', 'N/A')
            url = r.get('url', 'N/A')
            # Use snippet/description if raw content wasn't fetched or is too long
            content_snippet = r.get('content') or r.get('description') or r.get('snippet') or "No content snippet available."
            # Truncate long snippets
            max_snippet_len = 500
            if len(content_snippet) > max_snippet_len:
                content_snippet = content_snippet[:max_snippet_len] + "..."

            context_parts.append(
                f"Source {i+1}:\n"
                f"  Title: {title}\n"
                f"  URL: {url}\n"
                # f"  Date: {r.get('published_date', 'N/A')}\n" # Date might be less reliable/useful
                f"  Snippet: {content_snippet}\n"
            )
        context = "\n---\n".join(context_parts)
        log.debug(f"Context prepared for Gemini:\n{context[:500]}...") # Log beginning of context

    except Exception as e:
         error_msg = f"Error preparing context for Gemini: {e}"
         log.exception(error_msg)
         return {**state, "error": format_error_message(error_msg)}


    # --- Call Gemini for Markdown Summary ---
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use a capable model, like 1.5 Flash or Pro
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or 'gemini-1.5-pro-latest'

        topic = state['topic']
        prompt_markdown = f"""
        **Objective:** Generate a concise, informative, and engaging newsletter summary about the latest developments for the topic: **"{topic}"**.

        **Sources:**
        --- START OF SOURCES ---
        {context}
        --- END OF SOURCES ---

        **Instructions:**
        1.  **Analyze:** Carefully review the provided sources to identify the most significant news, updates, and key developments related to "{topic}". Ignore minor or irrelevant information.
        2.  **Structure (Markdown):** Create a summary in Markdown format with the following sections:
            *   **Catchy Title:** A main title for the newsletter (e.g., "{topic}: Weekly Digest", "{topic} Highlights").
            *   **Introduction (1-2 sentences):** Briefly state the main theme or highlight of this update period.
            *   **Key Developments (3-5 bullet points or short paragraphs):** Summarize the most important findings. Start each with a bolded sub-heading or use clear bullet points.
            *   **Source Citations:** For each key point, cite the relevant source(s) using the source number, like this: `(Source 1)` or `(Sources 2, 3)`. *Do not include the full URL directly in the Markdown summary.*
            *   **Concluding thought (Optional):** A brief closing remark or outlook.
        3.  **Tone:** Professional, objective, yet accessible and engaging.
        4.  **Language:** ENGLISH.
        5.  **Conciseness:** Keep the summary brief and to the point. Focus on novelty and significance.
        6.  **No New Info:** If the sources genuinely contain no significant new information, state that clearly (e.g., "No major updates found for {topic} this period based on the sources.").

        **Output Format:** Pure Markdown.
        """

        log.info("Generating Markdown summary with Gemini...")
        response_markdown = model.generate_content(
            prompt_markdown,
            generation_config=genai.types.GenerationConfig(temperature=0.5) # Adjust temperature for creativity/factuality
            )

        # Safety check (essential for Gemini)
        if not response_markdown.parts:
            block_reason = response_markdown.prompt_feedback.block_reason.name if hasattr(response_markdown, 'prompt_feedback') and response_markdown.prompt_feedback.block_reason else "Unknown"
            safety_ratings = response_markdown.prompt_feedback.safety_ratings if hasattr(response_markdown, 'prompt_feedback') else "N/A"
            error_msg = f"Gemini response was blocked. Reason: {block_reason}. Ratings: {safety_ratings}"
            log.error(error_msg)
            return {**state, "error": format_error_message(f"Content generation blocked by safety filters ({block_reason}).")}

        summary_markdown = response_markdown.text
        log.info("Markdown summary generated successfully.")
        log.debug(f"Generated Markdown:\n{summary_markdown[:500]}...")

    except Exception as e:
        error_msg = f"Gemini API call for Markdown summary failed: {e}"
        log.exception(error_msg)
        return {**state, "error": format_error_message(f"Gemini Summarization Error: {e}")}

    # --- Call Gemini for HTML Conversion (or use a library) ---
    # Option 1: Use Gemini again (simpler setup, might cost more)
    try:
        prompt_html = f"""
        **Objective:** Convert the following Markdown newsletter summary into a clean, well-formatted HTML email body.

        **Markdown Input:**
        --- START MARKDOWN ---
        {summary_markdown}
        --- END MARKDOWN ---

        **Source URLs (for linking):**
        {chr(10).join([f"Source {i+1}: {r.get('url', '#')}" for i, r in enumerate(tavily_results)])}

        **Instructions:**
        1.  **HTML Structure:** Create a standard HTML structure suitable for email clients (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`). Include basic meta tags (charset, viewport).
        2.  **Inline CSS:** Use **inline CSS** for styling to ensure maximum compatibility across email clients. Avoid `<style>` blocks in the `<head>` if possible.
        3.  **Styling:** Apply simple, professional styling. Suggestions:
            *   Font: Arial, Helvetica, sans-serif.
            *   Colors: Use a clean palette (e.g., blues, grays). `#333` for text, `#0056b3` for links/headings.
            *   Layout: Use `<div>`s or `<table>`s for basic structure if needed. Ensure readability with padding and margins. Max-width around 600-800px, centered.
            *   Headings: Use `<h1>`, `<h2>`, `<h3>` appropriately.
            *   Links: Make source citations `(Source X)` clickable links pointing to the correct URL from the list provided above. Links should be clearly identifiable (e.g., color, underline).
        4.  **Content:** Retain ALL content and meaning from the Markdown. Convert Markdown elements (bold, bullets) to their HTML equivalents (`<strong>`, `<ul><li>`).
        5.  **Clean Output:** Provide only the complete HTML code, starting with `<!DOCTYPE html>` and ending with `</html>`. Do not include explanations or backticks.

        **Output Format:** Raw HTML code.
        """

        log.info("Generating HTML version with Gemini...")
        response_html = model.generate_content(
             prompt_html,
             generation_config=genai.types.GenerationConfig(temperature=0.2) # Lower temp for formatting
        )

        if not response_html.parts:
             # Handle blocked response similarly to markdown
            block_reason = response_html.prompt_feedback.block_reason.name if hasattr(response_html, 'prompt_feedback') and response_html.prompt_feedback.block_reason else "Unknown"
            error_msg = f"Gemini HTML generation blocked. Reason: {block_reason}."
            log.error(error_msg)
            # Fallback: Send the Markdown summary directly? Or use a basic template.
            # For now, treat as error state for HTML.
            html_content = f"<p>Error generating HTML email format. Raw summary:</p><pre>{summary_markdown}</pre>"
            summary_error = state.get("error") # Keep previous error if any
            return {**state, "structured_summary": summary_markdown, "html_content": html_content, "error": summary_error or format_error_message(error_msg)}


        html_content = response_html.text
        # Basic cleanup: remove potential markdown backticks if Gemini adds them
        html_content = html_content.strip().replace("```html", "").replace("```", "")
        log.info("HTML content generated successfully.")
        log.debug(f"Generated HTML:\n{html_content[:500]}...")


    except Exception as e:
        error_msg = f"Gemini API call for HTML conversion failed: {e}"
        log.exception(error_msg)
        # Fallback: Use Markdown or a very basic HTML structure
        html_content = f"""
        <!DOCTYPE html><html><head><title>Newsletter</title></head><body>
        <h1>Summary</h1><pre>{summary_markdown}</pre>
        <p>(Error occurred during HTML formatting)</p>
        </body></html>
        """
        summary_error = state.get("error") # Keep previous error if any
        return {**state, "structured_summary": summary_markdown, "html_content": html_content, "error": summary_error or format_error_message(f"Gemini HTML Error: {e}")}

    # Option 2: Use a Python library like `markdown2` (requires adding dependency)
    # import markdown2
    # try:
    #     log.info("Converting Markdown to HTML using markdown2 library...")
    #     extras = [" PADDING", "cuddled-lists", "target-blank-links", "tables", "fenced-code-blocks"]
    #     html_content_body = markdown2.markdown(summary_markdown, extras=extras)
    #     # Wrap in basic HTML structure
    #     html_content = f"""
    #         <!DOCTYPE html><html><head><title>Newsletter: {state['topic']}</title>
    #         <style> /* Add basic inline styles here or link CSS */ </style>
    #         </head><body>{html_content_body}</body></html>"""
    #     log.info("HTML generated using markdown2.")
    # except Exception as e:
    #     error_msg = f"Markdown to HTML conversion failed: {e}"
    #     log.exception(error_msg)
    #     html_content = f"<p>Error formatting summary.</p><pre>{summary_markdown}</pre>" # Fallback
    #     summary_error = state.get("error")
    #     return {**state, "structured_summary": summary_markdown, "html_content": html_content, "error": summary_error or format_error_message(error_msg)}


    # --- Final State Update ---
    return {**state, "structured_summary": summary_markdown, "html_content": html_content, "error": None} # Clear error if this stage succeeded


def send_email_node(state: GraphState) -> GraphState:
    """
    Node to send the generated summary as an HTML email.
    """
    log.info("Node 'send_email_node': Preparing email dispatch.")

    # --- Pre-checks ---
    if state.get("error"):
        log.warning(f"Skipping email dispatch due to previous error: {state['error']}")
        return state # Pass the error through

    recipient = state.get("user_email")
    topic = state.get("topic", "Your Topic")
    timestamp = state.get("timestamp", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')) # Use provided or fallback
    html_body = state.get('html_content')
    text_body = state.get('structured_summary') # Fallback plain text

    if not recipient:
        error_msg = "Recipient email address is missing. Cannot send email."
        log.error(error_msg)
        return {**state, "error": error_msg}

    if not html_body and not text_body:
         error_msg = "Email content (HTML or text) is missing. Cannot send empty email."
         log.error(error_msg)
         return {**state, "error": error_msg}

    # Ensure there's at least some text body as fallback
    if not text_body:
        text_body = "Please view this email in an HTML-compatible client."
        # Or try to strip HTML tags from html_body as a basic text version

    # --- Prepare Email Content ---
    subject = f"Daily Newsletter: Updates on '{topic}' - {timestamp}"

    # Add a basic wrapper if the generated HTML doesn't include full structure
    if html_body and "<!DOCTYPE html>" not in html_body.lower():
        log.debug("Wrapping generated HTML snippet in a basic email template.")
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 20px auto; padding: 0; background-color: #f4f4f4; }}
                .container {{ background-color: #ffffff; padding: 25px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .header {{ background-color: #0056b3; color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; font-size: 0.85em; color: #777; padding-top: 20px; border-top: 1px solid #ddd; margin-top: 20px; }}
                a {{ color: #0056b3; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                h1, h2, h3 {{ color: #004080; }} /* Darker blue for headings */
                strong {{ color: #004080; }}
                 ul {{ padding-left: 20px; }}
                 li {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>{topic} Update</h1></div>
                <div class="content">
                    {html_body}
                </div>
                <div class="footer">
                    <p>This automated newsletter was generated on {timestamp}.</p>
                    <p>© {datetime.now().year} News Aggregator Service</p>
                </div>
            </div>
        </body>
        </html>
        """

    # --- Send Email ---
    log.info(f"Attempting to send email to {recipient} with subject '{subject}'")
    success = send_email(
        recipient_email=recipient,
        subject=subject,
        body=text_body, # Plain text fallback
        html_body=html_body # HTML primary content
    )

    if success:
        log.info("Email sent successfully.")
        # No state change needed, just pass through
        return state
    else:
        error_msg = "Email sending failed. Check sender credentials and logs."
        log.error(error_msg)
        # Keep existing error if there was one, otherwise set this one
        final_error = state.get("error") or error_msg
        return {**state, "error": format_error_message(final_error)}


# --- Graph Construction ---

def build_graph() -> StateGraph:
    """
    Builds and compiles the LangGraph StateGraph for the newsletter workflow.

    Returns:
        A compiled LangGraph application.
    """
    log.info("Building LangGraph workflow...")
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("fetch_data", fetch_tavily_data)
    workflow.add_node("summarize", summarize_with_gemini)
    workflow.add_node("send_notification", send_email_node)
    log.debug("Nodes added to workflow.")

    # Define edges and entry point
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "summarize")
    workflow.add_edge("summarize", "send_notification")
    workflow.add_edge("send_notification", END) # End the graph after sending email
    log.debug("Edges defined in workflow.")

    # Compile the graph
    app = workflow.compile()
    log.info("LangGraph workflow compiled successfully.")
    return app


# --- Standalone Test Execution ---
if __name__ == '__main__':
    print("--- LangGraph Standalone Test ---")
    # Ensure .env is loaded for standalone run
    from dotenv import load_dotenv
    load_dotenv()

    if config.load_credentials_from_env():
        # Ensure a recipient email is set for testing
        if not config.USER_EMAIL:
             config.USER_EMAIL = "test@example.com" # Default test recipient
             print(f"WARNING: USER_EMAIL not in env, using default for test: {config.USER_EMAIL}")

        print("Credentials loaded. Building graph...")
        test_graph = build_graph()

        print("\n--- Test Case 1: Valid Topic ---")
        test_topic = "Latest developments in Large Language Models"
        print(f"Topic: {test_topic}")
        print(f"Recipient: {config.USER_EMAIL}")

        inputs = GraphState(
            topic=test_topic,
            tavily_results=[],
            structured_summary="",
            html_content="",
            error=None,
            user_email=config.USER_EMAIL,
            timestamp=datetime.now(pytz.timezone('Europe/Paris')).strftime('%Y-%m-%d %H:%M %Z') # Example timestamp
        )

        print("\nInvoking graph...")
        results = test_graph.invoke(inputs)

        print("\n--- Final Graph State (Test Case 1) ---")
        from pprint import pprint
        # Avoid printing potentially huge HTML/results, show summary and error
        print(f"Topic: {results.get('topic')}")
        print(f"User Email: {results.get('user_email')}")
        print(f"Error: {results.get('error')}")
        print("\n--- Generated Summary (Markdown - Test Case 1) ---")
        print(results.get('structured_summary', 'No summary generated.'))
        # print("\n--- Generated HTML (First 500 chars - Test Case 1) ---")
        # print(results.get('html_content', 'No HTML generated.')[:500] + "...")

        if results.get('error'):
            print(f"\n*** TEST FAILED (Test Case 1) with error: {results['error']} ***")
        else:
            print("\n*** TEST COMPLETED (Test Case 1) - Check email and logs. ***")


        # print("\n--- Test Case 2: Topic with No Recent News (Simulated) ---")
        # You might need to mock Tavily to return empty results for this test reliably.
        # Or use a very obscure topic.
        # test_topic_no_news = "History of the Pet Rock Market 2024"
        # inputs_no_news = GraphState(...)
        # results_no_news = test_graph.invoke(inputs_no_news)
        # ... check results ...

    else:
        print("\nERROR: Could not load credentials from environment variables (.env).")
        print("Please ensure TAVILY_API_KEY, GEMINI_API_KEY, SENDER_EMAIL, SENDER_APP_PASSWORD, USER_EMAIL are set in your .env file to run the test.")

    print("\n--- LangGraph Standalone Test Finished ---")