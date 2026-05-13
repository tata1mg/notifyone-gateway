import logging
from typing import Optional

logger = logging.getLogger()

REDIS_KEY_PREFIX = 'rate_limit:send_notification'


class RateLimiter:
    """
    Fixed-window rate limiter backed by Redis.

    Uses INCR + EXPIRE to count requests per source_identifier within a
    rolling window. Fail-open: any Redis error is logged as a warning and
    the request is allowed through.
    """

    _instance: Optional['RateLimiter'] = None

    def __init__(self, redis_client, max_requests: int, window_seconds: int):
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    @classmethod
    def initialize(cls, redis_client, max_requests: int, window_seconds: int) -> 'RateLimiter':
        """Create and store the singleton RateLimiter instance."""
        cls._instance = cls(redis_client, max_requests, window_seconds)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Optional['RateLimiter']:
        return cls._instance

    @staticmethod
    def build_key(identifier: str) -> str:
        return '{}:{}'.format(REDIS_KEY_PREFIX, identifier)

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Returns True if the request is within the rate limit, False if exceeded.

        On any Redis error, logs a warning and returns True (fail-open).
        """
        key = self.build_key(identifier)
        try:
            count = await self._redis.incr(key)
            if count == 1:
                # First request in this window — set the TTL
                await self._redis.expire(key, self._window_seconds)
            return count <= self._max_requests
        except Exception as exc:
            logger.warning(
                'RateLimiter: Redis error for identifier=%s — failing open. '
                'Error: %s',
                identifier,
                exc,
            )
            return True
