"""
Structured JSON logging configuration with correlation IDs.
Logs include notification_id, idempotency_key, user_id for complete traceability.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# Context variables for correlation IDs
_notification_id: ContextVar[Optional[str]] = ContextVar('notification_id', default=None)
_idempotency_key: ContextVar[Optional[str]] = ContextVar('idempotency_key', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def set_context(
    notification_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Set correlation context variables"""
    if notification_id:
        _notification_id.set(notification_id)
    if idempotency_key:
        _idempotency_key.set(idempotency_key)
    if user_id:
        _user_id.set(user_id)
    if request_id:
        _request_id.set(request_id)


def clear_context() -> None:
    """Clear all context variables"""
    _notification_id.set(None)
    _idempotency_key.set(None)
    _user_id.set(None)
    _request_id.set(None)


def get_context() -> Dict[str, Optional[str]]:
    """Get current correlation context"""
    return {
        "notification_id": _notification_id.get(),
        "idempotency_key": _idempotency_key.get(),
        "user_id": _user_id.get(),
        "request_id": _request_id.get()
    }


class CorrelationIdFilter(logging.Filter):
    """Add correlation IDs to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.notification_id = _notification_id.get() or "-"
        record.idempotency_key = _idempotency_key.get() or "-"
        record.user_id = _user_id.get() or "-"
        record.request_id = _request_id.get() or "-"
        return True


class JsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with correlation IDs and timestamps"""
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to JSON log"""
        super().add_fields(log_record, record, message_dict)
        
        # Add ISO timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add correlation IDs
        log_record['notification_id'] = getattr(record, 'notification_id', '-')
        log_record['idempotency_key'] = getattr(record, 'idempotency_key', '-')
        log_record['user_id'] = getattr(record, 'user_id', '-')
        log_record['request_id'] = getattr(record, 'request_id', '-')
        
        # Add service info
        log_record['service'] = 'notification-push-service'
        log_record['level'] = record.levelname
        
        # Remove redundant fields
        log_record.pop('message', None)
        log_record.pop('asctime', None)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging"""
    # Create handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    
    # Format logs as JSON
    formatter = JsonFormatter('%(message)s %(levelname)s %(name)s')
    handler.setFormatter(formatter)
    
    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Configure app loggers
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    
    # Suppress verbose libraries
    logging.getLogger('aio_pika').setLevel(logging.WARNING)
    logging.getLogger('asyncpg').setLevel(logging.WARNING)
    logging.getLogger('redis').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with context support"""
    return logging.getLogger(name)
