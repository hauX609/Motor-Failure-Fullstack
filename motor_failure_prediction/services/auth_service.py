"""
Authentication service for Motor Monitoring System.
Handles OTP, password hashing, and session management.
"""

import secrets
import hashlib
import hmac
import sqlite3
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from config import (
    OTP_EXPIRY_MINUTES, SESSION_EXPIRY_HOURS, 
    OTP_RESEND_COOLDOWN_SECONDS, OTP_MAX_REQUESTS_PER_HOUR,
    DEV_OTP_IN_RESPONSE, now_iso
)
from models.database import db_manager
from services.email_service import email_service
from utils.errors import (
    AuthenticationError, NotFoundError, RateLimitError,
    ValidationError, DatabaseError
)


logger = logging.getLogger(__name__)


class AuthenticationService:
    """Handles authentication, OTP, and session management."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with per-user random salt (PBKDF2-HMAC-SHA256)."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100_000
        )
        return f"{salt}${password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, expected_hash = stored_hash.split('$', 1)
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100_000
            ).hex()
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False
    
    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP."""
        return f"{secrets.randbelow(1_000_000):06d}"
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def cleanup_expired_auth_data() -> None:
        """Clean up expired OTP and session records."""
        try:
            current_time = now_iso()
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM otp_codes WHERE expires_at < ? OR consumed = 1",
                    (current_time,)
                )
                cursor.execute(
                    "DELETE FROM auth_sessions WHERE expires_at < ? OR revoked = 1",
                    (current_time,)
                )
                conn.commit()
        except DatabaseError:
            logger.warning("Auth cleanup skipped due to error")
        except Exception as e:
            logger.warning(f"Auth cleanup skipped due to error: {e}")
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict]:
        """Get user from valid session token."""
        if not token:
            return None
        
        try:
            AuthenticationService.cleanup_expired_auth_data()
            
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT u.user_id, u.username, u.email, u.role, u.is_active
                    FROM auth_sessions s
                    JOIN users u ON u.user_id = s.user_id
                    WHERE s.token = ? AND s.revoked = 0 
                    AND s.expires_at > ? AND u.is_active = 1
                    """,
                    (token, now_iso())
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            return None
    
    @staticmethod
    def get_alert_email_recipients() -> list:
        """Get list of users subscribed to email alerts."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT email FROM users 
                    WHERE is_active = 1 AND email_notifications = 1 
                    AND email IS NOT NULL
                    """
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Failed to get alert recipients: {e}")
            return []
    
    @staticmethod
    def otp_rate_limit_status(user_id: int) -> Dict[str, int]:
        """Get OTP rate limit status for a user."""
        now = datetime.now()
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        now_time = now.isoformat()
        
        try:
            with db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get last OTP timestamp
                cursor.execute(
                    """
                    SELECT created_at FROM otp_codes
                    WHERE user_id = ? AND purpose = 'login'
                    ORDER BY otp_id DESC LIMIT 1
                    """,
                    (user_id,)
                )
                last_row = cursor.fetchone()
                
                # Count requests in last hour
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM otp_codes
                    WHERE user_id = ? AND purpose = 'login' AND created_at >= ?
                    """,
                    (user_id, one_hour_ago)
                )
                requests_last_hour = int(cursor.fetchone()[0])
            
            # Calculate cooldown
            cooldown_remaining = 0
            if last_row and last_row['created_at']:
                last_created = datetime.fromisoformat(last_row['created_at'])
                elapsed = int((datetime.fromisoformat(now_time) - last_created).total_seconds())
                cooldown_remaining = max(0, OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            
            remaining_this_hour = max(0, OTP_MAX_REQUESTS_PER_HOUR - requests_last_hour)
            
            return {
                'cooldown_remaining_seconds': cooldown_remaining,
                'requests_last_hour': requests_last_hour,
                'remaining_this_hour': remaining_this_hour
            }
        
        except Exception as e:
            logger.error(f"Error checking OTP rate limit: {e}")
            raise DatabaseError(f"Failed to check rate limit: {str(e)}")
    
    @staticmethod
    def issue_login_otp(user_id: int, email: str) -> Dict[str, str]:
        """Create OTP and send via email."""
        try:
            otp_code = AuthenticationService.generate_otp()
            expires_at = (
                datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
            ).isoformat()
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Invalidate previous OTPs
                cursor.execute(
                    """
                    UPDATE otp_codes SET consumed = 1 
                    WHERE user_id = ? AND purpose = 'login' AND consumed = 0
                    """,
                    (user_id,)
                )
                
                # Create new OTP
                cursor.execute(
                    """
                    INSERT INTO otp_codes 
                    (user_id, otp_code, purpose, expires_at, consumed, created_at)
                    VALUES (?, ?, 'login', ?, 0, ?)
                    """,
                    (user_id, otp_code, expires_at, now_iso())
                )
                conn.commit()
            
            # Send OTP email
            sent, reason = email_service.send_otp_email(email, otp_code)
            
            result = {
                'email': email,
                'otp_expires_at': expires_at,
                'email_delivery': 'sent' if sent else f'not_sent: {reason}'
            }
            
            # Include OTP in response if SMTP failed (dev mode)
            if not sent and DEV_OTP_IN_RESPONSE:
                result['dev_otp'] = otp_code
            
            return result
        
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error issuing OTP: {e}")
            raise DatabaseError(f"Failed to issue OTP: {str(e)}")


# Global authentication service instance
auth_service = AuthenticationService()
