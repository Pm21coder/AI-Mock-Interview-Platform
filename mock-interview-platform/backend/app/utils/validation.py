"""
Input validation utilities to prevent injection attacks and DoS.
"""
import re
from typing import Any, Tuple


def validate_string(value: Any, min_length: int = 0, max_length: int = 10000, 
                   field_name: str = "value") -> Tuple[bool, str]:
    """
    Validate a string input with length constraints.
    
    Args:
        value: The value to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        field_name: Name of field for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, str):
        return False, f"{field_name} must be a string"
    
    if len(value) < min_length:
        return False, f"{field_name} must be at least {min_length} characters"
    
    if len(value) > max_length:
        return False, f"{field_name} must not exceed {max_length} characters"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(email, str):
        return False, "Email must be a string"
    
    # RFC 5322 simplified validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 254:
        return False, "Email must not exceed 254 characters"
    
    return True, ""


def validate_integer(value: Any, min_value: int = None, max_value: int = None,
                    field_name: str = "value") -> Tuple[bool, str]:
    """
    Validate an integer with optional bounds.
    
    Args:
        value: The value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of field for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a valid integer"
    
    if min_value is not None and int_value < min_value:
        return False, f"{field_name} must be at least {min_value}"
    
    if max_value is not None and int_value > max_value:
        return False, f"{field_name} must not exceed {max_value}"
    
    return True, ""


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string by removing excessive whitespace and limiting length.
    
    Args:
        value: The string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Remove leading/trailing whitespace and limit consecutive whitespace
    sanitized = " ".join(value.split())
    
    # Limit length
    return sanitized[:max_length]


def validate_file_size(file_obj, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Validate uploaded file size.
    
    Args:
        file_obj: File object from request.files
        max_size_mb: Maximum size in megabytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_obj:
        return False, "No file provided"
    
    # Seek to end to get file size
    file_obj.seek(0, 2)
    file_size = file_obj.tell()
    file_obj.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        return False, f"File must not exceed {max_size_mb}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, ""


def validate_json_size(data: Any, max_size_kb: int = 100) -> Tuple[bool, str]:
    """
    Validate JSON payload size to prevent DoS.
    
    Args:
        data: The data structure to validate
        max_size_kb: Maximum size in kilobytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import json
    
    try:
        json_str = json.dumps(data, default=str)
        size_kb = len(json_str.encode('utf-8')) / 1024
        
        if size_kb > max_size_kb:
            return False, f"Request payload must not exceed {max_size_kb}KB"
        
        return True, ""
    except Exception as e:
        return False, f"Could not validate JSON size: {str(e)}"
