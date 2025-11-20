"""Rate limiting service using Redis with sliding window algorithm."""

import logging
import time
from typing import Tuple

import redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis with sliding window algorithm.

    Implements graceful degradation - if Redis is unavailable,
    requests are allowed through (fail open).
    """

    def __init__(self) -> None:
        """Initialize rate limiter with Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self.redis_client.ping()
            self.available = True
            logger.info("Rate limiter initialized with Redis")
        except RedisError as e:
            logger.warning(f"Redis unavailable for rate limiting: {e}")
            self.redis_client = None
            self.available = False

    def check_rate_limit(
        self, key: str, limit: int, window: int = 3600
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Unique identifier for rate limit (e.g., user:123:endpoint)
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 1 hour)

        Returns:
            Tuple of (allowed, remaining, reset_time)
            - allowed: True if request should be allowed
            - remaining: Number of requests remaining
            - reset_time: Unix timestamp when limit resets
        """
        if not self.available or not settings.RATE_LIMIT_ENABLED:
            # Fail open - allow request if Redis unavailable
            return True, limit, int(time.time() + window)

        try:
            current_time = int(time.time())
            window_start = current_time // window * window
            reset_time = window_start + window

            # Redis key with window bucket
            redis_key = f"ratelimit:{key}:{window_start}"

            # Get current count
            current_count = self.redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0

            if current_count >= limit:
                # Rate limit exceeded
                remaining = 0
                return False, remaining, reset_time

            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window * 2)  # TTL for cleanup
            pipe.execute()

            remaining = limit - (current_count + 1)
            return True, remaining, reset_time

        except RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open
            return True, limit, int(time.time() + window)

    def get_remaining(self, key: str, limit: int, window: int = 3600) -> int:
        """
        Get remaining requests in current window.

        Args:
            key: Unique identifier for rate limit
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Number of requests remaining
        """
        if not self.available:
            return limit

        try:
            current_time = int(time.time())
            window_start = current_time // window * window
            redis_key = f"ratelimit:{key}:{window_start}"

            current_count = self.redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0

            return max(0, limit - current_count)

        except RedisError as e:
            logger.error(f"Failed to get remaining: {e}")
            return limit

    def reset_limit(self, key: str, window: int = 3600) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Unique identifier for rate limit
            window: Time window in seconds
        """
        if not self.available:
            return

        try:
            current_time = int(time.time())
            window_start = current_time // window * window
            redis_key = f"ratelimit:{key}:{window_start}"

            self.redis_client.delete(redis_key)
            logger.info(f"Reset rate limit for key: {key}")

        except RedisError as e:
            logger.error(f"Failed to reset limit: {e}")

    def check_cost_limit(
        self, key: str, cost: int, limit: int, window: int = 3600
    ) -> Tuple[bool, int, int]:
        """
        Check cost-based rate limit (credits system).

        Args:
            key: Unique identifier
            cost: Cost of current operation in credits
            limit: Maximum credits allowed in window
            window: Time window in seconds

        Returns:
            Tuple of (allowed, remaining_credits, reset_time)
        """
        if not self.available or not settings.RATE_LIMIT_ENABLED:
            return True, limit, int(time.time() + window)

        try:
            current_time = int(time.time())
            window_start = current_time // window * window
            reset_time = window_start + window

            redis_key = f"ratelimit:cost:{key}:{window_start}"

            # Get current credits used
            current_cost = self.redis_client.get(redis_key)
            current_cost = int(current_cost) if current_cost else 0

            if current_cost + cost > limit:
                # Credit limit exceeded
                remaining = 0
                return False, remaining, reset_time

            # Increment cost
            pipe = self.redis_client.pipeline()
            pipe.incrby(redis_key, cost)
            pipe.expire(redis_key, window * 2)
            pipe.execute()

            remaining = limit - (current_cost + cost)
            return True, remaining, reset_time

        except RedisError as e:
            logger.error(f"Cost limit check failed: {e}")
            return True, limit, int(time.time() + window)


# Global rate limiter instance
rate_limiter = RateLimiter()
