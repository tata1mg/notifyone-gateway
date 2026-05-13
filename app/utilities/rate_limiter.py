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
        identifier = identifier[:256]
        return '{}:{}'.format(REDIS_KEY_PREFIX, identifier)

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Returns True if the request is within the rate limit, False if exceeded.

        Uses an atomic Redis pipeline (MULTI/EXEC) to INCR and EXPIRE together,
        guaranteeing the key always has a TTL. EXPIRE is called on every request
        so the key is never left without a TTL even if an earlier EXPIRE failed.

        On any Redis error, logs a warning and returns True (fail-open).
        """
        key = self.build_key(identifier)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self._window_seconds)
                count, _ = await pipe.execute()
            return count <= self._max_requests
        except Exception as exc:
            logger.warning(
                'RateLimiter: Redis error for identifier=%s — failing open. '
                'Error: %s',
                identifier,
                exc,
            )
            return True
