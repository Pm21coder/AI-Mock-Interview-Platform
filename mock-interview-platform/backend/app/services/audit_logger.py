"""
Audit logging service for tracking financial transactions and security events.
"""
import logging
from datetime import datetime
from typing import Dict, Any
import json
from pathlib import Path


class AuditLogger:
    """
    Tracks financial transactions and security events for compliance.
    """
    
    def __init__(self, log_dir: str = None):
        """
        Initialize the audit logger.
        
        Args:
            log_dir: Directory to store audit logs. Defaults to backend/logs/
        """
        self.log_dir = Path(log_dir or 'logs')
        self.log_dir.mkdir(exist_ok=True)
        
        # Create separate loggers for different audit categories
        self.payment_logger = self._create_logger('payment_audit', 'payment_transactions.log')
        self.auth_logger = self._create_logger('auth_audit', 'auth_events.log')
        self.security_logger = self._create_logger('security_audit', 'security_events.log')
    
    def _create_logger(self, name: str, filename: str) -> logging.Logger:
        """Create a logger with file handler."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = self.log_dir / filename
        handler = logging.FileHandler(str(log_file))
        
        # Create formatter - includes timestamp and JSON structure
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Clear any existing handlers and add new one
        logger.handlers = [handler]
        
        return logger
    
    def log_payment_initiated(self, user_id: str, tier: str, amount: int, 
                             currency: str, order_id: str = None):
        """
        Log when a payment is initiated.
        
        Args:
            user_id: User attempting payment
            tier: Subscription tier (basic, pro, etc)
            amount: Amount in smallest currency unit (paise, cents, etc)
            currency: Currency code (INR, USD, etc)
            order_id: Payment provider order ID
        """
        event = {
            'event': 'payment_initiated',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id),
            'tier': tier,
            'amount': amount,
            'currency': currency,
            'order_id': order_id,
        }
        self.payment_logger.info(json.dumps(event))
    
    def log_payment_completed(self, user_id: str, tier: str, amount: int,
                             order_id: str, payment_id: str, status: str = 'success'):
        """
        Log when a payment completes.
        
        Args:
            user_id: User who made payment
            tier: Subscription tier
            amount: Amount in smallest currency unit
            order_id: Payment provider order ID
            payment_id: Payment provider payment ID
            status: Payment status (success, failed, etc)
        """
        event = {
            'event': 'payment_completed',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id),
            'tier': tier,
            'amount': amount,
            'order_id': order_id,
            'payment_id': payment_id,
            'status': status,
        }
        self.payment_logger.info(json.dumps(event))
    
    def log_payment_failed(self, user_id: str, tier: str, order_id: str,
                          error_reason: str):
        """
        Log payment failures.
        
        Args:
            user_id: User attempting payment
            tier: Subscription tier
            order_id: Payment provider order ID
            error_reason: Reason for failure (sanitized)
        """
        event = {
            'event': 'payment_failed',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id),
            'tier': tier,
            'order_id': order_id,
            'error_reason': error_reason[:200],  # Limit length
        }
        self.payment_logger.warning(json.dumps(event))
    
    def log_subscription_upgraded(self, user_id: str, old_tier: str, new_tier: str):
        """Log subscription tier changes."""
        event = {
            'event': 'subscription_upgraded',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id),
            'old_tier': old_tier,
            'new_tier': new_tier,
        }
        self.payment_logger.info(json.dumps(event))
    
    def log_auth_success(self, email: str, method: str = 'password'):
        """
        Log successful authentication.
        
        Args:
            email: User email
            method: Authentication method (password, token, etc)
        """
        event = {
            'event': 'auth_success',
            'timestamp': datetime.utcnow().isoformat(),
            'email': email[:50],  # Limit length
            'method': method,
        }
        self.auth_logger.info(json.dumps(event))
    
    def log_auth_failure(self, email: str, reason: str):
        """
        Log failed authentication attempts.
        
        Args:
            email: User email
            reason: Reason for failure (sanitized)
        """
        event = {
            'event': 'auth_failure',
            'timestamp': datetime.utcnow().isoformat(),
            'email': email[:50],  # Limit length
            'reason': reason[:100],  # Limit length
        }
        self.auth_logger.warning(json.dumps(event))
    
    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str, limit: str):
        """
        Log rate limit violations.
        
        Args:
            ip_address: Client IP address
            endpoint: API endpoint that was rate-limited
            limit: Rate limit that was exceeded
        """
        event = {
            'event': 'rate_limit_exceeded',
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': ip_address,
            'endpoint': endpoint,
            'limit': limit,
        }
        self.security_logger.warning(json.dumps(event))
    
    def log_suspicious_activity(self, user_id: str, activity_type: str, details: Dict[str, Any]):
        """
        Log suspicious activities for investigation.
        
        Args:
            user_id: User involved
            activity_type: Type of suspicious activity
            details: Additional details about the activity
        """
        event = {
            'event': 'suspicious_activity',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id),
            'activity_type': activity_type,
            'details': details,
        }
        self.security_logger.warning(json.dumps(event))


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
