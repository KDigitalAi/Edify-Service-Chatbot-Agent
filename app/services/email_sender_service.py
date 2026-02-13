"""
Email Sender Service
Handles SMTP email sending functionality.
Uses configuration from environment variables.
"""

from typing import Dict, Any
from app.core.config import settings
import smtplib
from email.message import EmailMessage
import logging
import re

logger = logging.getLogger(__name__)


class EmailSenderService:
    """
    Service for sending emails via SMTP.
    Uses configuration from settings (loaded from .env).
    """
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.email_from_name = settings.EMAIL_FROM_NAME
        
        # Validate configuration on initialization
        self._validate_config()
    
    def _validate_config(self):
        """Validate SMTP configuration."""
        if not self.smtp_host:
            logger.warning("SMTP_HOST not configured")
        if not self.smtp_username:
            logger.warning("SMTP_USERNAME not configured")
        if not self.smtp_password:
            logger.warning("SMTP_PASSWORD not configured")
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            Dictionary with result:
            {
                "success": True/False,
                "error": None or error_message
            }
        """
        # Validate inputs
        if not subject or not subject.strip():
            return {
                "success": False,
                "error": "Email subject cannot be empty"
            }
        
        if not body or not body.strip():
            return {
                "success": False,
                "error": "Email body cannot be empty"
            }
        
        if not self._is_valid_email(to_email):
            return {
                "success": False,
                "error": f"Invalid email address: {to_email}"
            }
        
        # Validate SMTP configuration
        if not self.smtp_host or not self.smtp_username or not self.smtp_password:
            return {
                "success": False,
                "error": "SMTP configuration incomplete. Please check SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD in .env"
            }
        
        try:
            # Create email message
            msg = EmailMessage()
            msg['From'] = f"{self.email_from_name} <{self.smtp_username}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.set_content(body)
            
            # Send email via SMTP
            logger.info(f"Attempting to send email to {to_email} via {self.smtp_host}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                # Authenticate
                server.login(self.smtp_username, self.smtp_password)
                
                # Send email
                server.send_message(msg)
            
            logger.info(f"Email successfully sent to {to_email}")
            
            return {
                "success": True,
                "error": None
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient email rejected: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP server disconnected: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        except TimeoutError as e:
            error_msg = f"SMTP connection timeout: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

