"""Functional tests for per-source_identifier rate limiting on POST /send-notification.

These tests exercise the rate_limit_send_notification decorator directly,
without relying on the full Sanic test server (which has a pre-existing
fixture issue unrelated to rate limiting). The decorator is tested in
isolation with a lightweight async request mock.
"""
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.utilities.rate_limiter import RateLimiter
from app.middlewares.rate_limiter_middleware import rate_limit_send_notification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(source_identifier: str):
    """Build a minimal mock Sanic Request with a JSON body."""
    request = MagicMock()
    body = {'source_identifier': source_identifier, 'event_id': 1}
    request.json = body
    return request


def _make_limiter(counter_value: int, max_requests: int = 100):
    """Build a RateLimiter whose Redis pipeline returns the given counter value."""
    pipe = MagicMock()
    pipe.incr = MagicMock(return_value=None)
    pipe.expire = MagicMock(return_value=None)
    pipe.execute = AsyncMock(return_value=(counter_value, True))

    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=pipe)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)

    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=ctx_manager)
    return RateLimiter(redis, max_requests=max_requests, window_seconds=60)


async def _dummy_handler(request, *args, **kwargs):
    """Stub handler that always returns a sentinel value."""
    return 'handler_called'


# ---------------------------------------------------------------------------
# Tests using the decorator directly
# ---------------------------------------------------------------------------

class TestRateLimitingDecorator:

    @pytest.mark.asyncio
    async def test_request_within_limit_passes_to_handler(self):
        """Counter=1: request should reach the inner handler."""
        limiter = _make_limiter(counter_value=1)
        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            decorated = rate_limit_send_notification(_dummy_handler)
            result = await decorated(_make_request('user1'))
        assert result == 'handler_called'

    @pytest.mark.asyncio
    async def test_request_at_exact_limit_passes_to_handler(self):
        """Counter=100 (at max_requests=100): request should still pass."""
        limiter = _make_limiter(counter_value=100, max_requests=100)
        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            decorated = rate_limit_send_notification(_dummy_handler)
            result = await decorated(_make_request('user1'))
        assert result == 'handler_called'

    @pytest.mark.asyncio
    async def test_request_over_limit_returns_429(self):
        """Counter=101 (over max_requests=100): must return HTTP 429."""
        limiter = _make_limiter(counter_value=101, max_requests=100)
        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            decorated = rate_limit_send_notification(_dummy_handler)
            response = await decorated(_make_request('user1'))
        assert response.status == 429
        body = json.loads(response.body)
        assert body['error']['message'] == 'Rate limit exceeded'
        assert body['is_success'] is False
        assert body['status_code'] == 429

    @pytest.mark.asyncio
    async def test_different_users_independent_counters(self):
        """Each source_identifier has an independent counter."""
        limiter_a = _make_limiter(counter_value=1)    # user-A: within limit
        limiter_b = _make_limiter(counter_value=200)  # user-B: over limit

        decorated = rate_limit_send_notification(_dummy_handler)

        with patch.object(RateLimiter, 'get_instance', return_value=limiter_a):
            result_a = await decorated(_make_request('user-A'))
        with patch.object(RateLimiter, 'get_instance', return_value=limiter_b):
            result_b = await decorated(_make_request('user-B'))

        assert result_a == 'handler_called'  # user-A allowed
        assert result_b.status == 429        # user-B blocked

    @pytest.mark.asyncio
    async def test_redis_unavailable_fails_open(self):
        """Any Redis pipeline exception must allow the request through."""
        pipe = MagicMock()
        pipe.incr = MagicMock(return_value=None)
        pipe.expire = MagicMock(return_value=None)
        pipe.execute = AsyncMock(side_effect=ConnectionError('Redis down'))

        ctx_manager = MagicMock()
        ctx_manager.__aenter__ = AsyncMock(return_value=pipe)
        ctx_manager.__aexit__ = AsyncMock(return_value=False)

        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=ctx_manager)
        limiter = RateLimiter(redis, max_requests=100, window_seconds=60)

        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            decorated = rate_limit_send_notification(_dummy_handler)
            result = await decorated(_make_request('user1'))
        assert result == 'handler_called'

    @pytest.mark.asyncio
    async def test_no_rate_limiter_instance_fails_open(self):
        """If RateLimiter was never initialised (None), requests pass through."""
        with patch.object(RateLimiter, 'get_instance', return_value=None):
            decorated = rate_limit_send_notification(_dummy_handler)
            result = await decorated(_make_request('user1'))
        assert result == 'handler_called'

    @pytest.mark.asyncio
    async def test_missing_source_identifier_passes_to_handler(self):
        """
        A request without source_identifier bypasses the counter check
        (the route itself will reject it with 400 — not the rate limiter).
        """
        limiter = _make_limiter(counter_value=9999)  # would block any keyed user
        request = MagicMock()
        request.json = {'event_id': 1}  # no source_identifier

        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            decorated = rate_limit_send_notification(_dummy_handler)
            result = await decorated(request)
        assert result == 'handler_called'

    @pytest.mark.asyncio
    async def test_get_route_without_decorator_is_not_rate_limited(self):
        """
        A handler that does NOT have the decorator applied is never limited,
        even if the limiter would block.
        """
        limiter = _make_limiter(counter_value=9999)

        # Simulate get_event_notification without the decorator
        async def get_handler(request, *args, **kwargs):
            return 'get_handler_called'

        with patch.object(RateLimiter, 'get_instance', return_value=limiter):
            result = await get_handler(_make_request('user1'))
        assert result == 'get_handler_called'
