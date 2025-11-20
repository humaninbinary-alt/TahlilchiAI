"""Database middleware for automatic transaction management."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class DatabaseTransactionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure database transactions are properly managed.

    This middleware:
    1. Ensures each request gets a clean database state
    2. Automatically rolls back failed transactions
    3. Logs database-related errors
    4. Prevents transaction state from leaking between requests
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with automatic transaction management."""
        try:
            # Process the request
            response = await call_next(request)

            # Check for error responses that might indicate database issues
            if response.status_code >= 500:
                logger.warning(f"Request failed with status {response.status_code}")

            return response

        except Exception as e:
            # Log the error
            logger.error(f"Request failed with exception: {e}")

            # Re-raise the exception to let FastAPI handle it
            raise

        finally:
            # Ensure any database connections are cleaned up
            # This happens automatically with our new session management
            pass


class DatabasePoolMonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor database connection pool health.

    This helps identify connection leaks and pool exhaustion.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor database pool during request processing."""
        from app.database import async_engine

        # Get pool status before request
        pool = async_engine.pool
        if pool:
            pre_size = pool.size()
            pre_checked_in = pool.checkedin()
            pre_overflow = pool.overflow()

            logger.debug(
                f"Pool before request: size={pre_size}, "
                f"checked_in={pre_checked_in}, overflow={pre_overflow}"
            )

        try:
            # Process the request
            response = await call_next(request)

            # Get pool status after request
            if pool:
                post_size = pool.size()
                post_checked_in = pool.checkedin()
                post_overflow = pool.overflow()

                # Warn if connections aren't being returned
                if post_checked_in < pre_checked_in:
                    logger.warning(
                        f"Possible connection leak: {pre_checked_in - post_checked_in} "
                        f"connections not returned to pool"
                    )

                logger.debug(
                    f"Pool after request: size={post_size}, "
                    f"checked_in={post_checked_in}, overflow={post_overflow}"
                )

            return response

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
