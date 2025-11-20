"""Performance monitoring middleware."""

import logging
import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Thresholds for slow operations (in seconds)
SLOW_REQUEST_THRESHOLD = 5.0
VERY_SLOW_REQUEST_THRESHOLD = 10.0


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Monitor and log slow requests."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Monitor request performance."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log slow requests
        if duration > VERY_SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Very slow request detected: {request.method} {request.url.path} "
                f"took {duration:.2f}s",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": duration,
                    "threshold": "very_slow",
                },
            )
        elif duration > SLOW_REQUEST_THRESHOLD:
            logger.info(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.2f}s",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": duration,
                    "threshold": "slow",
                },
            )

        return response


def log_slow_operation(operation_name: str, duration: float, context: dict = None):
    """Log slow operation with context."""
    thresholds = {
        "database_query": 1.0,
        "api_call": 2.0,
        "llm_generation": 10.0,
        "document_processing": 60.0,
    }

    threshold = thresholds.get(operation_name, 1.0)

    if duration > threshold:
        extra = {
            "operation": operation_name,
            "duration_seconds": duration,
            "threshold_seconds": threshold,
        }
        if context:
            extra.update(context)

        logger.warning(
            f"Slow operation: {operation_name} took {duration:.2f}s "
            f"(threshold: {threshold}s)",
            extra=extra,
        )
