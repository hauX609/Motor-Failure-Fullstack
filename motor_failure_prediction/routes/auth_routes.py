"""
Authentication routes for Motor Monitoring System.
Handles user registration, login, OTP verification, and logout.
"""

from flask import Blueprint, request, jsonify
import logging
import re
import sqlite3
from urllib.parse import quote

from config import (
    now_iso,
    SESSION_EXPIRY_HOURS,
    OTP_MAX_VERIFY_ATTEMPTS,
    OTP_VERIFY_LOCKOUT_MINUTES,
)
from services.auth_service import auth_service
from services.email_service import email_service
from models.database import db_manager
from utils.validators import Validator
from routes.decorators import api_key_required
from utils.errors import (
    ValidationError, AuthenticationError, ConflictError,
    RateLimitError, NotFoundError, DatabaseError
)


logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account."""
    try:
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        
        # Validate inputs
        if not Validator.validate_username(username):
            return jsonify({'error': 'Invalid username. Use 3-30 chars: letters, numbers, _.-'}), 400
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not Validator.validate_password(password):
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Create user
        created_at = now_iso()
        duplicate_row = db_manager.execute_query(
            "SELECT user_id FROM users WHERE username = ? OR email = ? LIMIT 1",
            (username, email),
            fetch_one=True,
        )
        if duplicate_row:
            return jsonify({'error': 'Username or email already exists'}), 409

        try:
            query = """
                INSERT INTO users (username, email, password_hash, role, email_notifications, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 'operator', 1, 1, ?, ?)
            """
            db_manager.execute_update(
                query,
                (username, email, auth_service.hash_password(password), created_at, created_at)
            )
        
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        return jsonify({
            'message': 'User registered successfully',
            'username': username,
            'email': email,
            'timestamp': now_iso()
        }), 201
    
    except ValidationError as e:
        return jsonify({'error': e.message}), 400
    except DatabaseError as e:
        # db_manager wraps sqlite IntegrityError; map duplicate user conflicts to 409.
        msg = (e.message or '').lower()
        if 'unique' in msg or 'constraint' in msg:
            return jsonify({'error': 'Username or email already exists'}), 409
        logger.error(f"Register database error: {e}")
        return jsonify({'error': 'Registration failed'}), 500
    except Exception as e:
        logger.error(f"Register error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """LoginUser with password, receive OTP."""
    try:
        data = request.get_json() or {}
        identifier = (data.get('identifier') or '').strip()
        password = data.get('password') or ''
        
        if not identifier or not password:
            return jsonify({'error': 'identifier and password are required'}), 400
        
        # Get user
        user = db_manager.get_user(identifier)
        if not user or not auth_service.verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Issue OTP
        otp_payload = auth_service.issue_login_otp(user['user_id'], user['email'])
        
        response = {
            'message': 'OTP generated. Verify using /auth/verify-otp',
            'email': otp_payload['email'],
            'otp_expires_at': otp_payload['otp_expires_at'],
            'email_delivery': otp_payload['email_delivery'],
            'timestamp': now_iso()
        }
        
        if 'dev_otp' in otp_payload:
            response['dev_otp'] = otp_payload['dev_otp']
        
        return jsonify(response)
    
    except AuthenticationError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP with rate limiting."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Get user
        user = db_manager.get_user_by_email(email)
        if not user or not user.get('is_active'):
            return jsonify({'error': 'User not found or inactive'}), 404
        
        # Check rate limits
        limit_status = auth_service.otp_rate_limit_status(user['user_id'])
        
        if limit_status['remaining_this_hour'] <= 0:
            return jsonify({
                'error': 'OTP request limit exceeded. Try again later.',
                'requests_last_hour': limit_status['requests_last_hour'],
                'max_per_hour': 5
            }), 429
        
        if limit_status['cooldown_remaining_seconds'] > 0:
            return jsonify({
                'error': 'Please wait before requesting another OTP.',
                'cooldown_remaining_seconds': limit_status['cooldown_remaining_seconds']
            }), 429
        
        # Issue new OTP
        otp_payload = auth_service.issue_login_otp(user['user_id'], user['email'])
        
        response = {
            'message': 'OTP resent successfully',
            'email': otp_payload['email'],
            'otp_expires_at': otp_payload['otp_expires_at'],
            'email_delivery': otp_payload['email_delivery'],
            'timestamp': now_iso()
        }
        
        if 'dev_otp' in otp_payload:
            response['dev_otp'] = otp_payload['dev_otp']
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        return jsonify({'error': 'Resend OTP failed'}), 500


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Exchange OTP for session token."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        otp_code = (data.get('otp') or '').strip()
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not Validator.validate_otp(otp_code):
            return jsonify({'error': 'OTP must be a 6-digit code'}), 400
        
        # Cleanup and verify OTP
        auth_service.cleanup_expired_auth_data()
        
        with db_manager.get_connection() as conn:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get user
            cursor.execute(
                """
                SELECT user_id, username, email, role, failed_otp_attempts, otp_locked_until
                FROM users
                WHERE email = ? AND is_active = 1
                """,
                (email,)
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Lockout check to mitigate OTP brute-force attempts.
            locked_until = user['otp_locked_until']
            if locked_until and locked_until > now_iso():
                return jsonify({
                    'error': 'Too many invalid OTP attempts. Try again later.',
                    'locked_until': locked_until
                }), 429
            
            # Verify OTP
            cursor.execute(
                """
                SELECT otp_id, expires_at FROM otp_codes
                WHERE user_id = ? AND otp_code = ? AND purpose = 'login' 
                AND consumed = 0 AND expires_at > ?
                ORDER BY otp_id DESC LIMIT 1
                """,
                (user['user_id'], otp_code, now_iso())
            )
            otp_row = cursor.fetchone()
            if not otp_row:
                current_attempts = int(user['failed_otp_attempts'] or 0) + 1
                lock_until = None
                if current_attempts >= OTP_MAX_VERIFY_ATTEMPTS:
                    from datetime import datetime, timedelta
                    lock_until = (datetime.now() + timedelta(minutes=OTP_VERIFY_LOCKOUT_MINUTES)).isoformat()
                    current_attempts = 0

                cursor.execute(
                    """
                    UPDATE users
                    SET failed_otp_attempts = ?, otp_locked_until = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (current_attempts, lock_until, now_iso(), user['user_id'])
                )
                conn.commit()

                return jsonify({'error': 'Invalid or expired OTP'}), 401
            
            # Mark OTP as consumed and create session
            cursor.execute("UPDATE otp_codes SET consumed = 1 WHERE otp_id = ?", (otp_row['otp_id'],))
            cursor.execute(
                """
                UPDATE users
                SET failed_otp_attempts = 0, otp_locked_until = NULL, updated_at = ?
                WHERE user_id = ?
                """,
                (now_iso(), user['user_id'])
            )
            
            token = auth_service.generate_session_token()
            from datetime import datetime, timedelta
            expires_at = (datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat()
            
            cursor.execute(
                """
                INSERT INTO auth_sessions (user_id, token, expires_at, revoked, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (user['user_id'], token, expires_at, now_iso())
            )
            conn.commit()
        
        return jsonify({
            'message': 'Login successful',
            'token_type': 'Bearer',
            'access_token': token,
            'expires_at': expires_at,
            'user': {
                'user_id': user['user_id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
        })
    
    except Exception as e:
        logger.error(f"Verify OTP error: {e}")
        return jsonify({'error': 'OTP verification failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout and revoke bearer token."""
    try:
        auth_header = request.headers.get('Authorization', '').strip()
        
        if not auth_header.lower().startswith('bearer '):
            return jsonify({'message': 'No bearer session to revoke'}), 200
        
        token = auth_header.split(' ', 1)[1].strip()
        query = "UPDATE auth_sessions SET revoked = 1 WHERE token = ?"
        db_manager.execute_update(query, (token,))
        
        return jsonify({'message': 'Logged out successfully', 'timestamp': now_iso()})
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@api_key_required
def auth_me():
    """Get current authenticated user details."""
    try:
        from flask import g
        user = getattr(g, 'current_user', None)
        
        if not user:
            return jsonify({'auth_mode': 'api_key', 'message': 'Authenticated via API key'}), 200
        
        return jsonify({'auth_mode': 'bearer', 'user': user, 'timestamp': now_iso()})
    
    except Exception as e:
        logger.error(f"Auth me error: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset token via email."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Get user
        user = db_manager.get_user_by_email(email)
        if not user or not user.get('is_active'):
            # Return success anyway for security (don't reveal if email exists)
            return jsonify({
                'message': 'If an account exists with this email, password reset link will be sent',
                'timestamp': now_iso()
            }), 200
        
        # Generate reset token
        reset_token = auth_service.generate_session_token()
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        try:
            query = """
                INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at)
                VALUES (?, ?, ?, 0, ?)
            """
            db_manager.execute_update(
                query,
                (user['user_id'], reset_token, expires_at, now_iso())
            )
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Failed to generate reset token'}), 500
        
        # Send email with reset link
        try:
            # Use frontend origin when available so users land on the UI reset page,
            # not the backend API host/port.
            frontend_origin = (request.headers.get('Origin') or '').strip()
            if not frontend_origin or not re.match(r'^https?://', frontend_origin):
                frontend_origin = 'http://localhost:8080'

            reset_link = (
                f"{frontend_origin.rstrip('/')}/reset-password"
                f"?token={quote(reset_token)}&email={quote(email)}"
            )
            email_service.send_password_reset_email(email, user.get('username', ''), reset_link)
        except Exception as e:
            logger.warning(f"Failed to send reset email: {e}")
            # Continue even if email fails in dev
        
        return jsonify({
            'message': 'If an account exists with this email, password reset link will be sent',
            'timestamp': now_iso()
        }), 200
    
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({'error': 'Password reset request failed'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token."""
    try:
        data = request.get_json() or {}
        token = (data.get('token') or '').strip()
        email = (data.get('email') or '').strip().lower()
        new_password = data.get('new_password') or ''
        
        if not token or not email or not new_password:
            return jsonify({'error': 'token, email, and new_password are required'}), 400
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not Validator.validate_password(new_password):
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Verify reset token
        with db_manager.get_connection() as conn:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get user
            cursor.execute(
                "SELECT user_id FROM users WHERE email = ? AND is_active = 1",
                (email,)
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Verify token exists, not used, and not expired
            cursor.execute(
                """
                SELECT token_id FROM password_reset_tokens
                WHERE user_id = ? AND token = ? AND used = 0 AND expires_at > ?
                """,
                (user['user_id'], token, now_iso())
            )
            reset_token_row = cursor.fetchone()
            if not reset_token_row:
                return jsonify({'error': 'Invalid or expired reset token'}), 401
            
            # Update password and mark token as used
            new_hash = auth_service.hash_password(new_password)
            cursor.execute(
                """
                UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?
                """,
                (new_hash, now_iso(), user['user_id'])
            )
            cursor.execute(
                """
                UPDATE password_reset_tokens SET used = 1 WHERE token_id = ?
                """,
                (reset_token_row['token_id'],)
            )
            conn.commit()
        
        return jsonify({
            'message': 'Password reset successfully',
            'timestamp': now_iso()
        }), 200
    
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500


@auth_bp.route('/admin/create-user', methods=['POST'])
@api_key_required
def admin_create_user():
    """Create a new user account (admin only)."""
    try:
        from flask import g
        current_user = getattr(g, 'current_user', None)
        
        # Check admin/owner role
        if not current_user or current_user.get('role') not in ['admin', 'owner']:
            return jsonify({'error': 'Unauthorized. Admin access required'}), 403
        
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        role = (data.get('role') or 'operator').strip().lower()
        
        # Validate inputs
        if not Validator.validate_username(username):
            return jsonify({'error': 'Invalid username. Use 3-30 chars: letters, numbers, _.-'}), 400
        
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not password:
            # Generate temporary password if not provided
            password = auth_service.generate_session_token()[:16]
        
        if not Validator.validate_password(password):
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        if role not in ['operator', 'supervisor', 'admin', 'owner']:
            return jsonify({'error': 'Invalid role. Must be operator, supervisor, admin, or owner'}), 400
        
        # Check for duplicates
        duplicate_row = db_manager.execute_query(
            "SELECT user_id FROM users WHERE username = ? OR email = ? LIMIT 1",
            (username, email),
            fetch_one=True,
        )
        if duplicate_row:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Create user
        created_at = now_iso()
        try:
            query = """
                INSERT INTO users (username, email, password_hash, role, email_notifications, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, ?, ?)
            """
            db_manager.execute_update(
                query,
                (username, email, auth_service.hash_password(password), role, created_at, created_at)
            )
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Send welcome email with credentials
        try:
            email_service.send_user_creation_email(email, username, password)
        except Exception as e:
            logger.warning(f"Failed to send user creation email: {e}")
        
        return jsonify({
            'message': 'User created successfully',
            'username': username,
            'email': email,
            'role': role,
            'temporary_password': password,
            'timestamp': now_iso()
        }), 201
    
    except Exception as e:
        logger.error(f"Admin create user error: {e}")
        return jsonify({'error': 'User creation failed'}), 500
