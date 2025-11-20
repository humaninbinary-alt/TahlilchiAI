"""Global error handling and tracking."""

import logging
import traceback
from collections import deque
from datetime import datetime
from typing import Any, Dict, List

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Store recent errors in memory (last 100)
recent_errors: deque = deque(maxlen=100)
error_counts: Dict[str, int] = {}


class ErrorInfo:
    """Structured error information."""

    def __init__(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str,
        request_context: Dict[str, Any],
        timestamp: datetime,
    ):
        """Initialize error info."""
        self.error_type = error_type
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.request_context = request_context
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "request_context": self.request_context,
            "timestamp": self.timestamp.isoformat(),
        }


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: FastAPI request
        exc: Exception that was raised

    Returns:
        JSON response with error details
    """
    # Get error details
    error_type = type(exc).__name__
    error_message = str(exc)
    stack_trace = traceback.format_exc()

    # Build request context
    request_context = {
        "method": request.method,
        "path": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
        "client_ip": request.client.host if request.client else "unknown",
    }

    # Add user context if available
    if hasattr(request.state, "user"):
        request_context["user_id"] = str(request.state.user.id)
        request_context["tenant_id"] = str(request.state.user.tenant_id)

    # Create error info
    error_info = ErrorInfo(
        error_type=error_type,
        error_message=error_message,
        stack_trace=stack_trace,
        request_context=request_context,
        timestamp=datetime.utcnow(),
    )

    # Store recent error
    recent_errors.append(error_info)

    # Track error count
    error_counts[error_type] = error_counts.get(error_type, 0) + 1

    # Log error with full context
    logger.error(
        f"Unhandled exception: {error_type}: {error_message}",
        extra={
            **request_context,
            "error_type": error_type,
            "error_message": error_message,
        },
        exc_info=True,
    )

    # Return user-friendly error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_context.get("request_id"),
        },
    )


def get_recent_errors(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent errors."""
    return [error.to_dict() for error in list(recent_errors)[-limit:]]


def get_error_counts() -> Dict[str, int]:
    """Get error counts by type."""
    return dict(error_counts)


def clear_error_tracking() -> None:
    """Clear error tracking (for testing)."""
    recent_errors.clear()
    error_counts.clear()
