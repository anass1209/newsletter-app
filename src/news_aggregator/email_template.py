# src/news_aggregator/email_template.py
import logging
import re
from datetime import datetime

def create_enhanced_email_template(topic, content, timestamp):
    """
    Create a professional, modern HTML email template
    
    Args:
        topic: Newsletter topic
        content: HTML content of the newsletter
        timestamp: Timestamp for the newsletter
        
    Returns:
        str: Complete HTML email template
    """
    
    # Sanitize content - make sure it doesn't have html/body tags
    if "<body" in content:
        # Extract just the content inside the body
        try:
            body_content = re.search(r'<body[^>]*>(.*?)<\/body>', content, re.DOTALL)
            if body_content:
                content = body_content.group(1)
        except Exception as e:
            logging.warning(f"Error extracting body content: {e}")
    
    # Remove any script tags for security
    content = content.replace('<script', '<!-- script').replace('</script>', '<!-- /script -->')
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title>Newsletter: {topic}</title>
        <style>
            /* Base styles */
            body, html {{
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f9f9f9;
            }}
            
            /* Typography */
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 0;
                margin-bottom: 1rem;
                color: #1a202c;
                font-weight: 700;
                line-height: 1.3;
            }}
            
            h1 {{ font-size: 28px; color: #2563eb; }}
            h2 {{ font-size: 24px; color: #1d4ed8; }}
            h3 {{ font-size: 20px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
            
            p {{ margin-top: 0; margin-bottom: 1rem; }}
            
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ color: #1d4ed8; text-decoration: underline; }}
            
            /* Layout container */
            .email-container {{
                max-width: 680px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }}
            
            /* Header */
            .header {{
                background: linear-gradient(120deg, #2563eb 0%, #1d4ed8 100%);
                color: white;
                padding: 30px 40px;
                text-align: center;
            }}
            
            .header h1 {{
                margin: 0;
                font-size: 30px;
                color: white;
                font-weight: 800;
                letter-spacing: -0.5px;
            }}
            
            .header p {{
                margin: 10px 0 0;
                opacity: 0.9;
                font-size: 16px;
            }}
            
            /* Content */
            .content {{
                padding: 40px;
                background-color: #ffffff;
            }}
            
            /* Info bar */
            .info-bar {{
                background-color: #f1f5f9;
                padding: 15px 40px;
                font-size: 14px;
                color: #64748b;
                border-bottom: 1px solid #e2e8f0;
                text-align: center;
            }}
            
            /* Article section */
            .article {{
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #f1f5f9;
            }}
            
            .article:last-child {{
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }}
            
            /* Source links */
            .source {{
                display: inline-block;
                background-color: #f8fafc;
                border-radius: 4px;
                padding: 4px 8px;
                margin-top: 5px;
                font-size: 14px;
                color: #64748b;
            }}
            
            /* Blockquotes */
            blockquote {{
                margin: 20px 0;
                padding: 15px 20px;
                background-color: #f8fafc;
                border-left: 4px solid #2563eb;
                font-style: italic;
                color: #475569;
            }}
            
            /* Lists */
            ul, ol {{
                padding-left: 20px;
            }}
            
            li {{
                margin-bottom: 8px;
            }}
            
            /* Footer */
            .footer {{
                background-color: #f8fafc;
                padding: 25px 40px;
                color: #64748b;
                font-size: 14px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
            }}
            
            .footer p {{
                margin: 5px 0;
            }}
            
            .social-links {{
                margin-top: 15px;
            }}
            
            .social-link {{
                display: inline-block;
                margin: 0 8px;
                color: #64748b;
            }}
            
            /* Responsive */
            @media screen and (max-width: 600px) {{
                .header, .content, .footer, .info-bar {{
                    padding: 20px;
                }}
                
                .header h1 {{
                    font-size: 24px;
                }}
                
                h1 {{ font-size: 24px; }}
                h2 {{ font-size: 20px; }}
                h3 {{ font-size: 18px; }}
            }}
            
            /* Image styling */
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
                margin: 10px 0;
            }}
            
            /* Table styling */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            
            th {{
                background-color: #f1f5f9;
                padding: 10px;
                text-align: left;
                font-weight: 600;
                color: #1e293b;
                border-bottom: 2px solid #e2e8f0;
            }}
            
            td {{
                padding: 10px;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            
            /* Button styling */
            .button {{
                display: inline-block;
                background-color: #2563eb;
                color: white !important;
                text-decoration: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: 600;
                text-align: center;
                margin: 10px 0;
            }}
            
            .button:hover {{
                background-color: #1d4ed8;
            }}
            
            /* Dark mode support */
            @media (prefers-color-scheme: dark) {{
                body {{
                    background-color: #1a202c;
                }}
                
                .email-container {{
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
                }}
            }}
        </style>
    </head>
    <body style="background-color: #f9f9f9; margin: 0; padding: 30px 0;">
        <!-- Preheader text (hidden) -->
        <div style="display: none; max-height: 0px; overflow: hidden;">
            Latest updates and insights about {topic} - Newsletter from Newsletter Monitor
        </div>
        
        <!-- Email container -->
        <div class="email-container">
            <!-- Header -->
            <div class="header">
                <h1>Newsletter Monitor</h1>
                <p>Latest insights on {topic}</p>
            </div>
            
            <!-- Info bar -->
            <div class="info-bar">
                Generated on {timestamp} • Curated just for you
            </div>
            
            <!-- Content -->
            <div class="content">
                {content}
                
                <!-- Read more button -->
                <div style="text-align: center; margin-top: 30px; margin-bottom: 10px;">
                    <a href="#" class="button">Read More On This Topic</a>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p>This newsletter was automatically generated based on your interests.</p>
                <p>©2025 Newsletter Monitor</p>
                <p><small>Powered by Tavily and Google Gemini</small></p>
                
                <div class="social-links">
                    <a href="#" class="social-link">Website</a> •
                    <a href="#" class="social-link">LinkedIn</a> •
                    <a href="#" class="social-link">Twitter</a>
                </div>
                
                <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">
                    If you no longer wish to receive these emails, you can <a href="#" style="color: #64748b;">unsubscribe</a>.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template