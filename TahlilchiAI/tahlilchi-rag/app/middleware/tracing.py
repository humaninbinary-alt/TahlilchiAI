"""Request tracing middleware for distributed tracing."""

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID and trace requests.

    Adds X-Request-ID header to all responses and logs request lifecycle.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with tracing."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Store in request state
        request.state.request_id = request_id

        # Add to logging context
        extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }

        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra=extra,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            extra["status_code"] = response.status_code
            extra["duration_ms"] = duration_ms

            log_level = logging.INFO
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING

            logger.log(
                log_level,
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms",
                extra=extra,
            )

            return response

        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            extra["duration_ms"] = duration_ms
            extra["error"] = str(e)

            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} duration={duration_ms:.2f}ms",
                extra=extra,
                exc_info=True,
            )
            raise
