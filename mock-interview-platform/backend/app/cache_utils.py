"""
Response caching utilities for API endpoints.
Reduces database queries and improves API response times.
"""
import time
from functools import wraps
from typing import Callable, Optional

# Simple in-memory cache with TTL
_cache_store = {}


def cache_response(ttl_seconds: int = 300):
    """
    Decorator to cache function responses for a specified TTL.
    
    Args:
        ttl_seconds: Time to live in seconds (default 5 minutes)
    
    Usage:
        @cache_response(ttl_seconds=60)
        def expensive_function(user_id):
            return get_data_from_db(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if cached value exists and is still valid
            if cache_key in _cache_store:
                cached_data, timestamp = _cache_store[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    return cached_data
            
            # If not cached or expired, call the function
            result = func(*args, **kwargs)
            
            # Store the result with current timestamp
            _cache_store[cache_key] = (result, time.time())
            
            return result
        
        return wrapper
    
    return decorator


def clear_cache(pattern: Optional[str] = None):
    """
    Clear cache entries matching a pattern or all if no pattern provided.
    
    Args:
        pattern: Optional pattern to match cache keys (e.g., "get_dashboard_stats")
    """
    global _cache_store
    
    if pattern is None:
        _cache_store.clear()
        return
    
    keys_to_delete = [k for k in _cache_store.keys() if pattern in k]
    for k in keys_to_delete:
        del _cache_store[k]


def optimize_response(data: dict) -> dict:
    """
    Remove unnecessary fields from API responses to reduce payload size.
    
    Args:
        data: Response data dictionary
    
    Returns:
        Optimized response with unnecessary fields removed
    """
    # Define fields that can be safely removed for specific response types
    unnecessary_fields = {
        '_id', '_debug', '_internal', 'password_hash', 'salt',
        'ip_address', 'user_agent', 'raw_response'
    }
    
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k not in unnecessary_fields}
    elif isinstance(data, list):
        return [optimize_response(item) if isinstance(item, dict) else item for item in data]
    
    return data
