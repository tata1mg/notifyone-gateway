import json
import logging
from functools import wraps

from sanic.response import json as sanic_json

from app.utilities.rate_limiter import RateLimiter

logger = logging.getLogger()


def rate_limit_send_notification(handler):
    """
    Decorator that enforces per-source_identifier rate limiting on the
    wrapped route handler.

    Reads the rate-limit config from the RATE_LIMITING section. If the
    section is missing or ENABLED is False, the decorator is a no-op.
    On limit exceeded, responds with HTTP 429. On any error (including
    missing body or Redis failure) it fails open.
    """
    @wraps(handler)
    async def wrapper(request, *args, **kwargs):
        rate_limiter = RateLimiter.get_instance()
        if rate_limiter is None:
            # Rate limiting not initialised — fail open
            return await handler(request, *args, **kwargs)

        try:
            body = request.json if request.json is not None else {}
        except Exception:
            body = {}

        source_identifier = body.get('source_identifier') or ''

        if source_identifier:
            allowed = await rate_limiter.check_rate_limit(source_identifier)
            if not allowed:
                logger.warning(
                    'RateLimiter: limit exceeded for source_identifier=%s',
                    source_identifier,
                )
                return sanic_json(
                    {
                        'error': {'message': 'Rate limit exceeded'},
                        'is_success': False,
                        'status_code': 429,
                    },
                    status=429,
                )

        return await handler(request, *args, **kwargs)

    return wrapper
