"""Prometheus metrics middleware."""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.metrics import (
    active_requests,
    request_duration_seconds,
    requests_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        """Collect metrics for request."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Increment active requests
        active_requests.inc()

        # Track request start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            method = request.method
            endpoint = request.url.path
            status = response.status_code

            # Increment request counter
            requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

            # Record request duration
            request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
                duration
            )

            return response

        finally:
            # Decrement active requests
            active_requests.dec()
