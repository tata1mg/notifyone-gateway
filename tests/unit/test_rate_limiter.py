"""Unit tests for app.utilities.rate_limiter.RateLimiter."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utilities.rate_limiter import RateLimiter, REDIS_KEY_PREFIX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_redis_mock(incr_side_effect=None, incr_return_value=1):
    """Return a mock that looks like an aioredis.Redis client."""
    redis = MagicMock()
    if incr_side_effect is not None:
        redis.incr = AsyncMock(side_effect=incr_side_effect)
    else:
        redis.incr = AsyncMock(return_value=incr_return_value)
    redis.expire = AsyncMock(return_value=True)
    return redis


def make_limiter(redis_mock, max_requests=100, window_seconds=60):
    return RateLimiter(redis_mock, max_requests, window_seconds)


# ---------------------------------------------------------------------------
# build_key
# ---------------------------------------------------------------------------

class TestBuildKey:
    def test_key_format(self):
        key = RateLimiter.build_key('user_abc')
        assert key == '{}:{}'.format(REDIS_KEY_PREFIX, 'user_abc')

    def test_key_includes_identifier(self):
        key = RateLimiter.build_key('order-PO12345')
        assert 'order-PO12345' in key


# ---------------------------------------------------------------------------
# check_rate_limit — happy path
# ---------------------------------------------------------------------------

class TestCheckRateLimitHappyPath:
    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        redis = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_first_request_sets_expire(self):
        redis = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis, window_seconds=60)
        await limiter.check_rate_limit('user1')
        redis.expire.assert_awaited_once_with(
            RateLimiter.build_key('user1'), 60
        )

    @pytest.mark.asyncio
    async def test_subsequent_request_does_not_reset_expire(self):
        redis = make_redis_mock(incr_return_value=2)
        limiter = make_limiter(redis)
        await limiter.check_rate_limit('user1')
        redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_request_at_exact_limit_allowed(self):
        redis = make_redis_mock(incr_return_value=100)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_request_uses_correct_redis_key(self):
        redis = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis)
        await limiter.check_rate_limit('my_identifier')
        redis.incr.assert_awaited_once_with(
            'rate_limit:send_notification:my_identifier'
        )


# ---------------------------------------------------------------------------
# check_rate_limit — limit exceeded
# ---------------------------------------------------------------------------

class TestCheckRateLimitExceeded:
    @pytest.mark.asyncio
    async def test_request_over_limit_rejected(self):
        redis = make_redis_mock(incr_return_value=101)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is False

    @pytest.mark.asyncio
    async def test_far_over_limit_rejected(self):
        redis = make_redis_mock(incr_return_value=999)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is False

    @pytest.mark.asyncio
    async def test_limit_is_per_identifier(self):
        """Different identifiers have independent counters (each starts fresh)."""
        redis_a = make_redis_mock(incr_return_value=101)
        redis_b = make_redis_mock(incr_return_value=1)
        limiter_a = make_limiter(redis_a, max_requests=100)
        limiter_b = make_limiter(redis_b, max_requests=100)
        assert await limiter_a.check_rate_limit('user_a') is False
        assert await limiter_b.check_rate_limit('user_b') is True


# ---------------------------------------------------------------------------
# check_rate_limit — fail-open on Redis errors
# ---------------------------------------------------------------------------

class TestCheckRateLimitFailOpen:
    @pytest.mark.asyncio
    async def test_connection_error_allows_request(self):
        redis = make_redis_mock(incr_side_effect=ConnectionError('refused'))
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_error_allows_request(self):
        redis = make_redis_mock(incr_side_effect=TimeoutError('timeout'))
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_generic_exception_allows_request(self):
        redis = make_redis_mock(incr_side_effect=Exception('unexpected'))
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_error_logs_warning(self, caplog):
        import logging
        redis = make_redis_mock(incr_side_effect=ConnectionError('down'))
        limiter = make_limiter(redis)
        with caplog.at_level(logging.WARNING):
            await limiter.check_rate_limit('user_x')
        assert any('user_x' in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# initialize / get_instance
# ---------------------------------------------------------------------------

class TestInitialize:
    def test_initialize_stores_instance(self):
        redis = make_redis_mock()
        instance = RateLimiter.initialize(redis, 50, 30)
        assert RateLimiter.get_instance() is instance

    def test_get_instance_returns_none_before_initialize(self):
        RateLimiter._instance = None
        assert RateLimiter.get_instance() is None

    def test_initialize_sets_max_requests(self):
        redis = make_redis_mock()
        instance = RateLimiter.initialize(redis, 42, 60)
        assert instance._max_requests == 42

    def test_initialize_sets_window(self):
        redis = make_redis_mock()
        instance = RateLimiter.initialize(redis, 100, 120)
        assert instance._window_seconds == 120
