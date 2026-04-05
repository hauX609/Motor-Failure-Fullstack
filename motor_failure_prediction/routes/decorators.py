"""
Authentication decorators for Motor Monitoring System.
Handles API key and bearer token validation.
"""

from functools import wraps
from flask import request, jsonify, g
import logging

from config import SECRET_API_KEY
from services.auth_service import auth_service


logger = logging.getLogger(__name__)


def api_key_required(f):
    """Decorator for endpoints requiring API key or bearer token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.current_user = None
        
        # Check for Bearer token first
        auth_header = request.headers.get('Authorization', '').strip()
        if auth_header.lower().startswith('bearer '):
            token = auth_header.split(' ', 1)[1].strip()
            user = auth_service.get_user_from_token(token)
            if user:
                g.current_user = user
                return f(*args, **kwargs)
        
        # Fall back to API key
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == SECRET_API_KEY:
            return f(*args, **kwargs)
        
        # Return appropriate error
        if auth_header.lower().startswith('bearer '):
            return jsonify({"error": "Unauthorized. Invalid or expired bearer token."}), 401
        
        if not api_key:
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized. Missing API key or bearer token."}), 401
        
        logger.warning(f"Unauthorized API key attempt from {request.remote_addr}")
        return jsonify({"error": "Unauthorized. Invalid API key."}), 401
    
    return decorated_function
