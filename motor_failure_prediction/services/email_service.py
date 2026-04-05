"""
Email service for Motor Monitoring System.
Handles all email operations with SMTP configuration.
"""

import smtplib
import logging
from email.message import EmailMessage
from typing import List, Tuple

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, 
    SMTP_FROM, SMTP_USE_TLS, OTP_EXPIRY_MINUTES
)
from utils.errors import ServiceUnavailableError


logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending operations."""
    
    def __init__(self):
        """Initialize email service."""
        pass
    
    @staticmethod
    def is_configured() -> bool:
        """Check if SMTP is properly configured."""
        return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)
    
    @staticmethod
    def send_email(subject: str, body: str, recipients: List[str]) -> Tuple[bool, str]:
        """Send email using SMTP configuration."""
        if not recipients:
            return False, 'No recipients configured'
        
        if not EmailService.is_configured():
            return False, 'SMTP configuration missing'
        
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = SMTP_FROM
            msg['To'] = ', '.join(recipients)
            msg.set_content(body)
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            return True, 'Email sent successfully'
        
        except Exception as e:
            logger.error(f"Email send failure: {e}")
            return False, str(e)
    
    @staticmethod
    def send_otp_email(email: str, otp_code: str) -> Tuple[bool, str]:
        """Send OTP email."""
        subject = 'Your Motor Monitoring OTP'
        body = (
            f"Your one-time password is: {otp_code}\n\n"
            f"This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.\n"
            "If you did not request this, please ignore this message."
        )
        return EmailService.send_email(subject, body, [email])
    
    @staticmethod
    def send_alert_email(motor_id: str, severity: str, message: str, 
                        recipients: List[str]) -> Tuple[bool, str]:
        """Send alert email."""
        subject = f"[{severity}] Motor Alert: {motor_id}"
        body = (
            f"Motor ID: {motor_id}\n"
            f"Severity: {severity}\n"
            f"Details: {message}\n"
        )
        return EmailService.send_email(subject, body, recipients)
    
    @staticmethod
    def send_batch_alert_email(alerts: List[dict], recipients: List[str]) -> Tuple[bool, str]:
        """Send batch alert email."""
        subject = f"[{len(alerts)}] Motor Alerts Generated"
        lines = [
            f"{alert['motor_id']} | {alert['severity']} | {alert['message']}"
            for alert in alerts
        ]
        body = "Batch alerts generated:\n\n" + "\n".join(lines)
        return EmailService.send_email(subject, body, recipients)
    
    @staticmethod
    def send_password_reset_email(email: str, username: str, reset_link: str) -> Tuple[bool, str]:
        """Send password reset email."""
        subject = 'Password Reset Request - Motor Monitoring System'
        body = (
            f"Hello {username},\n\n"
            "You requested to reset your password. Click the link below to proceed:\n\n"
            f"{reset_link}\n\n"
            "This link is valid for 1 hour.\n\n"
            "If you did not request this, please ignore this message or contact support.\n"
            "Your password will not be changed until you click the link and set a new password."
        )
        return EmailService.send_email(subject, body, [email])
    
    @staticmethod
    def send_user_creation_email(email: str, username: str, temporary_password: str) -> Tuple[bool, str]:
        """Send new user creation email with temporary credentials."""
        subject = 'Welcome to Motor Monitoring System - Account Created'
        body = (
            f"Hello {username},\n\n"
            "Your account has been successfully created by an administrator.\n\n"
            "Login Credentials:\n"
            f"Email/Username: {email}\n"
            f"Temporary Password: {temporary_password}\n\n"
            "Please log in and change your password at your earliest convenience.\n"
            "For security, we recommend changing your password on first login.\n\n"
            "If you have any questions, please contact your system administrator."
        )
        return EmailService.send_email(subject, body, [email])


# Global email service instance
email_service = EmailService()
