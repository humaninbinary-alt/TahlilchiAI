"""Rate limiting middleware."""

import logging
from typing import Callable, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.services.auth.jwt_service import JWTService
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _extract_identity(request: Request) -> Tuple[str | None, str | None]:
    """
    Extract user and tenant identifiers from the JWT token if present.

    Returns:
        Tuple of (user_id, tenant_id) as strings or (None, None) if unavailable.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None, None

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = JWTService.verify_token(token, token_type="access")
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        request.state.token_payload = payload
        return user_id, tenant_id
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to extract identity from token: %s", exc)
        return None, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.

    Adds rate limit headers to all responses and provides
    basic IP-based rate limiting for unauthenticated requests.
    """

    # Endpoints to bypass rate limiting
    BYPASS_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",  # Has its own stricter limits
        "/metrics",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""

        # Check for admin bypass token
        admin_token = request.headers.get("X-Admin-Token")
        if admin_token == settings.ADMIN_BYPASS_TOKEN:
            response = await call_next(request)
            response.headers["X-RateLimit-Status"] = "bypassed"
            return response

        # Bypass certain paths
        if request.url.path in self.BYPASS_PATHS:
            return await call_next(request)

        # Extract identity early for downstream middlewares
        user_id, tenant_id = _extract_identity(request)
        if user_id and not hasattr(request.state, "auth_user_id"):
            request.state.auth_user_id = user_id
        if tenant_id and not hasattr(request.state, "auth_tenant_id"):
            request.state.auth_tenant_id = tenant_id

        # Check if Redis is available
        if not rate_limiter.available:
            response = await call_next(request)
            response.headers["X-RateLimit-Status"] = "unavailable"
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers if set by decorator
        if hasattr(request.state, "rate_limit_headers"):
            for header, value in request.state.rate_limit_headers.items():
                response.headers[header] = value

        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting for all requests (fallback).

    Applied before endpoint-specific limits as a safety net.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply global rate limit."""

        # Skip for bypass paths
        if request.url.path in RateLimitMiddleware.BYPASS_PATHS:
            return await call_next(request)

        # Check admin bypass
        admin_token = request.headers.get("X-Admin-Token")
        if admin_token == settings.ADMIN_BYPASS_TOKEN:
            return await call_next(request)

        # Determine identity (user -> tenant -> IP)
        user_id = getattr(request.state, "auth_user_id", None)
        tenant_id = getattr(request.state, "auth_tenant_id", None)

        if user_id:
            identifier = f"user:{user_id}:global"
            limit = settings.RATE_LIMIT_FREE_USER
        elif tenant_id:
            identifier = f"tenant:{tenant_id}:global"
            limit = settings.RATE_LIMIT_FREE_TENANT
        else:
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{client_ip}:global"
            limit = 200  # Higher limit for anonymous clients

        # Check global rate limit
        allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            identifier, limit, window=3600
        )

        if not allowed:
            import time

            retry_after = reset_time - int(time.time())

            return Response(
                content='{"error":"rate_limit_exceeded","message":"Global rate limit exceeded"}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        # Continue processing
        response = await call_next(request)

        # Add global rate limit headers
        response.headers["X-RateLimit-Global-Limit"] = str(limit)
        response.headers["X-RateLimit-Global-Remaining"] = str(remaining)

        return response
