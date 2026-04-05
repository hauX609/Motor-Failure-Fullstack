"""
Custom exceptions and error handling for Motor Monitoring System.
Ensures consistent error handling across all modules.
"""


class MotorMonitoringError(Exception):
    """Base exception for motor monitoring system."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(MotorMonitoringError):
    """Raised when validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(MotorMonitoringError):
    """Raised when authentication fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class AuthorizationError(MotorMonitoringError):
    """Raised when authorization fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403)


class NotFoundError(MotorMonitoringError):
    """Raised when resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class ConflictError(MotorMonitoringError):
    """Raised when resource already exists."""
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class RateLimitError(MotorMonitoringError):
    """Raised when rate limit exceeded."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=429)
        self.details = details or {}


class ServiceUnavailableError(MotorMonitoringError):
    """Raised when external service unavailable."""
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class DatabaseError(MotorMonitoringError):
    """Raised when database operation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)
