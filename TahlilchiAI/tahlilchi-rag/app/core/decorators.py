"""Decorators for API endpoints."""

import functools
import logging
from typing import Callable, Literal

from fastapi import HTTPException, Request, status

from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

RateLimitScope = Literal["ip", "user", "tenant", "endpoint"]


def rate_limit(
    limit: int,
    window: int = 3600,
    scope: RateLimitScope = "user",
    cost: int = 1,
):
    """
    Rate limit decorator for API endpoints.

    Args:
        limit: Maximum requests/credits allowed in window
        window: Time window in seconds (default: 1 hour)
        scope: Rate limit scope (ip/user/tenant/endpoint)
        cost: Cost in credits for cost-based limiting

    Example:
        @router.post("/chats")
        @rate_limit(limit=20, window=3600, scope="user")
        async def create_chat(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request: Request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                logger.warning("Rate limit decorator: Request object not found")
                return await func(*args, **kwargs)

            # Build rate limit key based on scope
            key_parts = []

            if scope == "ip":
                client_ip = request.client.host if request.client else "unknown"
                key_parts.append(f"ip:{client_ip}")

            elif scope == "user":
                # Get user from request state (set by auth middleware)
                user = getattr(request.state, "user", None)
                if user:
                    key_parts.append(f"user:{user.id}")
                else:
                    # Fall back to IP if no user
                    client_ip = request.client.host if request.client else "unknown"
                    key_parts.append(f"ip:{client_ip}")

            elif scope == "tenant":
                user = getattr(request.state, "user", None)
                if user:
                    key_parts.append(f"tenant:{user.tenant_id}")
                else:
                    # Fall back to IP
                    client_ip = request.client.host if request.client else "unknown"
                    key_parts.append(f"ip:{client_ip}")

            elif scope == "endpoint":
                key_parts.append(f"endpoint:{request.url.path}")

            # Add endpoint to key for more granular limiting
            key_parts.append(request.url.path.replace("/", ":"))
            rate_limit_key = ":".join(key_parts)

            # Check rate limit
            if cost > 1:
                # Cost-based limiting
                allowed, remaining, reset_time = rate_limiter.check_cost_limit(
                    rate_limit_key, cost, limit, window
                )
            else:
                # Request-based limiting
                allowed, remaining, reset_time = rate_limiter.check_rate_limit(
                    rate_limit_key, limit, window
                )

            # Add rate limit headers to response
            if hasattr(request.state, "rate_limit_headers"):
                request.state.rate_limit_headers.update(
                    {
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(reset_time),
                    }
                )
            else:
                request.state.rate_limit_headers = {
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                }

            if not allowed:
                retry_after = reset_time - int(__import__("time").time())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again in {retry_after // 60} minutes.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                    },
                )

            # Execute endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator
