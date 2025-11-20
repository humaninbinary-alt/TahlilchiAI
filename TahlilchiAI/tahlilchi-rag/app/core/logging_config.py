"""Structured logging configuration for production observability."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add service name
        log_record["service"] = "tahlilchi-api"

        # Add log level
        log_record["level"] = record.levelname

        # Add context from record if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "tenant_id"):
            log_record["tenant_id"] = record.tenant_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms


def setup_logging() -> None:
    """Configure application logging."""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Determine log format based on environment
    if settings.ENVIRONMENT == "production":
        # JSON logging for production
        formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    else:
        # Human-readable logging for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,  # Keep 30 days
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # File handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get logger with context support."""
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding context to logs."""

    def __init__(self, **kwargs):
        """Initialize log context."""
        self.context = kwargs
        self.logger = logging.getLogger()

    def __enter__(self):
        """Enter context."""
        for key, value in self.context.items():
            setattr(self.logger, key, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        for key in self.context.keys():
            if hasattr(self.logger, key):
                delattr(self.logger, key)
