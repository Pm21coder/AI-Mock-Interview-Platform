"""
Error handling utilities to prevent information disclosure.
Sanitizes error messages before sending to clients.
"""
import logging
from flask import jsonify, current_app


class AppError(Exception):
    """
    Base application error with a safe message for clients.
    Internal details are logged but never exposed to the client.
    """
    def __init__(self, message: str, internal_details: str = None, status_code: int = 500):
        self.message = message  # Safe message for client
        self.internal_details = internal_details or message  # Full details for logs
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppError):
    """Raised when input validation fails."""
    def __init__(self, message: str, internal_details: str = None):
        super().__init__(message, internal_details, 400)


class AuthenticationError(AppError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed", internal_details: str = None):
        super().__init__(message, internal_details, 401)


class AuthorizationError(AppError):
    """Raised when user lacks required permissions."""
    def __init__(self, message: str = "You don't have permission to access this resource", 
                 internal_details: str = None):
        super().__init__(message, internal_details, 403)


class ResourceNotFoundError(AppError):
    """Raised when a requested resource doesn't exist."""
    def __init__(self, message: str = "Resource not found", internal_details: str = None):
        super().__init__(message, internal_details, 404)


class ConflictError(AppError):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    def __init__(self, message: str, internal_details: str = None):
        super().__init__(message, internal_details, 409)


class RateLimitError(AppError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message, message, 429)


class ExternalServiceError(AppError):
    """Raised when an external service fails (Razorpay, MongoDB, etc)."""
    def __init__(self, service_name: str, internal_details: str = None):
        message = f"{service_name} is temporarily unavailable. Please try again later."
        super().__init__(message, internal_details, 503)


def sanitize_error_message(error_msg: str, log_level: str = "error") -> str:
    """
    Sanitize error messages to prevent information disclosure.
    Removes implementation details like file paths, SQL queries, etc.
    """
    if not isinstance(error_msg, str):
        return "An unexpected error occurred"
    
    # Don't expose file paths, database details, or stack traces
    dangerous_patterns = [
        r'/[a-zA-Z0-9\/_\-\.]*\.py',  # Python file paths
        r'File "[^"]+", line \d+',     # Python traceback
        r'SELECT|INSERT|UPDATE|DELETE', # SQL queries
        r'mongodb://.*',               # Database URIs
        r'Authorization|X-API-Key',    # Credential headers
        r'token|secret|key|password',  # Sensitive keywords (case-insensitive)
    ]
    
    sanitized = error_msg
    for pattern in dangerous_patterns:
        import re
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
    
    return sanitized[:500]  # Limit length


def handle_app_error(error: AppError) -> tuple:
    """
    Handle AppError exceptions with proper logging and sanitization.
    
    Args:
        error: AppError instance
        
    Returns:
        Tuple of (json_response, status_code)
    """
    # Log full internal details
    logger = current_app.logger if current_app else logging.getLogger(__name__)
    logger.error(
        f"{error.__class__.__name__}: {error.internal_details}",
        exc_info=True
    )
    
    return jsonify({'error': error.message}), error.status_code


def handle_generic_error(error: Exception) -> tuple:
    """
    Handle unexpected errors by sanitizing and logging.
    
    Args:
        error: Any exception
        
    Returns:
        Tuple of (json_response, status_code)
    """
    logger = current_app.logger if current_app else logging.getLogger(__name__)
    
    # Log full error
    logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
    
    # Return safe message to client
    safe_message = "An unexpected error occurred. Please try again later."
    return jsonify({'error': safe_message}), 500
