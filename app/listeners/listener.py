import asyncio
import logging

from torpedo import CONFIG
from torpedo.constants import ListenerEventTypes

from app.services import EventNotification

logger = logging.getLogger()


async def setup_dispatch_notification(app, loop):
    EventNotification.setup()


async def setup_rate_limiter(app, loop):
    """Initialise the Redis-backed rate limiter at server start."""
    try:
        import aioredis

        rate_limiting_config = CONFIG.config.get('RATE_LIMITING') or {}
        if not rate_limiting_config.get('ENABLED', False):
            logger.info('RateLimiter: disabled via config, skipping initialisation')
            return

        redis_host = rate_limiting_config.get('REDIS_HOST', 'localhost')
        redis_port = rate_limiting_config.get('REDIS_PORT', 6379)
        redis_db = rate_limiting_config.get('REDIS_DB', 0)
        max_requests = rate_limiting_config.get('MAX_REQUESTS_PER_MINUTE', 100)
        window_seconds = rate_limiting_config.get('WINDOW_SECONDS', 60)
        connection_timeout = rate_limiting_config.get('CONNECTION_TIMEOUT', 2)

        redis_client = aioredis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            socket_connect_timeout=connection_timeout,
            socket_timeout=connection_timeout,
        )

        from app.utilities.rate_limiter import RateLimiter
        RateLimiter.initialize(redis_client, max_requests, window_seconds)
        logger.info(
            'RateLimiter: initialised — host=%s port=%s db=%s max=%s window=%ss',
            redis_host, redis_port, redis_db, max_requests, window_seconds,
        )
    except Exception as exc:
        logger.warning(
            'RateLimiter: failed to initialise, rate limiting disabled. Error: %s',
            exc,
        )


other_listeners = [
    (setup_dispatch_notification, ListenerEventTypes.AFTER_SERVER_START.value),
    (setup_rate_limiter, ListenerEventTypes.AFTER_SERVER_START.value),
]
