"""
Email sender module for sending notifications via SMTP.
"""
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending email notifications via SMTP."""
    
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, 
                 smtp_password: str, from_email: str, use_ssl: bool = False):
        """
        Initialize EmailSender.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            use_ssl: If True, use SMTP_SSL. If False, use SMTP with STARTTLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_ssl = use_ssl
    
    def _create_html_email(self, new_urls: Dict[str, List[str]], 
                          total_new: int) -> str:
        """Create HTML email body."""
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 20px;
                }}
                .summary {{
                    background-color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .source {{
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-left: 4px solid #3498db;
                }}
                .url-list {{
                    list-style-type: none;
                    padding-left: 0;
                }}
                .url-list li {{
                    margin: 8px 0;
                    padding: 5px;
                    background-color: #fff;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                }}
                .url-list a {{
                    color: #3498db;
                    text-decoration: none;
                    word-break: break-all;
                }}
                .url-list a:hover {{
                    text-decoration: underline;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <h1> Daily Ransomware Links</h1>
            
            <div class="summary">
                <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                <strong>Total New URLs:</strong> {total_new}
            </div>
        """
        
        if total_new == 0:
            html += """
            <p> No new URLs discovered since the last run. All sources are up to date.</p>
            """
        else:
            for source, urls in new_urls.items():
                if urls:
                    html += f"""
                    <div class="source">
                        <h2> {source}</h2>
                        <p><strong>{len(urls)} new URL(s)</strong></p>
                        <ul class="url-list">
                    """
                    for url in urls:
                        html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
                    html += """
                        </ul>
                    </div>
                    """
        
        html += """
            <div class="footer">
                <p>This is an automated report from your Daily URL Scraper.</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _create_text_email(self, new_urls: Dict[str, List[str]], 
                          total_new: int) -> str:
        """Create plain text email body."""
        text = f"""
 Daily Ransomware Links
{'=' * 50}

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total New URLs: {total_new}

"""
        
        if total_new == 0:
            text += " No new URLs discovered since the last run.\n"
        else:
            for source, urls in new_urls.items():
                if urls:
                    text += f"\n{source}\n{'-' * len(source)}\n"
                    text += f"{len(urls)} new URL(s):\n\n"
                    for url in urls:
                        text += f"  • {url}\n"
                    text += "\n"
        
        text += "\n" + "=" * 50 + "\n"
        text += "This is an automated report from your Daily URL Scraper.\n"
        
        return text
    
    def send_email(self, to_email: str, new_urls: Dict[str, List[str]], 
                   total_new: int) -> bool:
        """Send email notification with new URLs."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily Ransomware Links"
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Create both plain text and HTML versions
            text_body = self._create_text_email(new_urls, total_new)
            html_body = self._create_html_email(new_urls, total_new)
            
            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Connect and send
            logger.info(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}")
            
            if self.use_ssl:
                # Use SSL from the start (typically port 465)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                # Use regular SMTP with STARTTLS (typically port 587)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()
            
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check your username and password.")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
        
        return False