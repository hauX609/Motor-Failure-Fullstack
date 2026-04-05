"""
Validation functions for Motor Monitoring System.
Centralizes all input validation logic.
"""

import re
from typing import Union
from utils.errors import ValidationError


class Validator:
    """Centralized validation utility class."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not email or not isinstance(email, str) or len(email) > 254:
            return False
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    @staticmethod
    def validate_motor_id(motor_id: str) -> bool:
        """Validate motor ID format with enhanced checks."""
        if not motor_id or not isinstance(motor_id, str):
            return False
        
        motor_id = motor_id.strip()
        if len(motor_id) == 0 or len(motor_id) > 50:
            return False
        
        # Check for basic SQL injection patterns
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/']
        if any(char in motor_id for char in dangerous_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_severity(severity: str) -> bool:
        """Validate alert severity."""
        valid_severities = ['Degrading', 'Critical', 'Warning']
        return severity in valid_severities
    
    @staticmethod
    def validate_motor_status(status: str) -> bool:
        """Validate motor status."""
        valid_statuses = ['Optimal', 'Degrading', 'Critical']
        return status in valid_statuses
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        if not username:
            return False
        return bool(re.match(r'^[A-Za-z0-9_.-]{3,30}$', username.strip()))
    
    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> bool:
        """Validate password strength."""
        if not password or not isinstance(password, str):
            return False
        return len(password) >= min_length
    
    @staticmethod
    def validate_otp(otp_code: str) -> bool:
        """Validate OTP format."""
        if not otp_code:
            return False
        return otp_code.isdigit() and len(otp_code) == 6
    
    @staticmethod
    def get_alert_severity_for_status(status: str) -> str:
        """Convert motor status to alert severity."""
        status_to_severity_map = {
            'Optimal': 'Warning',
            'Degrading': 'Degrading',
            'Critical': 'Critical'
        }
        return status_to_severity_map.get(status, 'Warning')
    
    @staticmethod
    def validate_limit(limit: int, max_limit: int = 1000, min_limit: int = 1) -> bool:
        """Validate pagination limit."""
        return min_limit <= limit <= max_limit
    
    @staticmethod
    def validate_days(days: int, max_days: int = 365, min_days: int = 1) -> bool:
        """Validate days parameter."""
        return min_days <= days <= max_days
