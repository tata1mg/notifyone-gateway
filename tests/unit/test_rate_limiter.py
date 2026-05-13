"""Unit tests for app.utilities.rate_limiter.RateLimiter."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utilities.rate_limiter import RateLimiter, REDIS_KEY_PREFIX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pipeline_mock(incr_return_value=1, expire_return_value=True,
                       execute_side_effect=None):
    """Return a mock aioredis pipeline (async context manager)."""
    pipe = MagicMock()
    pipe.incr = MagicMock(return_value=None)   # queues the command
    pipe.expire = MagicMock(return_value=None)  # queues the command
    if execute_side_effect is not None:
        pipe.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        pipe.execute = AsyncMock(return_value=(incr_return_value, expire_return_value))
    return pipe


def make_redis_mock(incr_return_value=1, expire_return_value=True,
                    pipeline_side_effect=None, execute_side_effect=None):
    """Return a mock that looks like an aioredis.Redis client with pipeline support."""
    redis = MagicMock()
    pipe = make_pipeline_mock(
        incr_return_value=incr_return_value,
        expire_return_value=expire_return_value,
        execute_side_effect=execute_side_effect,
    )

    # pipeline() is used as `async with redis.pipeline(transaction=True) as pipe`
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=pipe)
    ctx_manager.__aexit__ = AsyncMock(return_value=False)

    if pipeline_side_effect is not None:
        redis.pipeline = MagicMock(side_effect=pipeline_side_effect)
    else:
        redis.pipeline = MagicMock(return_value=ctx_manager)

    return redis, pipe


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

    def test_key_caps_identifier_at_256_chars(self):
        long_id = 'x' * 300
        key = RateLimiter.build_key(long_id)
        suffix = key[len(REDIS_KEY_PREFIX) + 1:]  # strip prefix and colon
        assert len(suffix) == 256

    def test_key_with_short_identifier_not_truncated(self):
        short_id = 'abc'
        key = RateLimiter.build_key(short_id)
        assert key.endswith(':abc')


# ---------------------------------------------------------------------------
# check_rate_limit — happy path
# ---------------------------------------------------------------------------

class TestCheckRateLimitHappyPath:
    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        redis, pipe = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_first_request_calls_expire_via_pipeline(self):
        """EXPIRE is enqueued in the pipeline on the very first request."""
        redis, pipe = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis, window_seconds=60)
        await limiter.check_rate_limit('user1')
        pipe.expire.assert_called_once_with(RateLimiter.build_key('user1'), 60)

    @pytest.mark.asyncio
    async def test_expire_also_called_when_counter_greater_than_one(self):
        """
        EXPIRE must be called on every request — not just when count==1.
        This prevents immortal keys if an earlier EXPIRE failed.
        """
        redis, pipe = make_redis_mock(incr_return_value=2)
        limiter = make_limiter(redis)
        await limiter.check_rate_limit('user1')
        pipe.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_called_when_counter_at_limit(self):
        """EXPIRE is called even when the counter equals max_requests."""
        redis, pipe = make_redis_mock(incr_return_value=100)
        limiter = make_limiter(redis, max_requests=100)
        await limiter.check_rate_limit('user1')
        pipe.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_called_when_counter_over_limit(self):
        """EXPIRE is called even when the counter exceeds max_requests."""
        redis, pipe = make_redis_mock(incr_return_value=101)
        limiter = make_limiter(redis, max_requests=100)
        await limiter.check_rate_limit('user1')
        pipe.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_at_exact_limit_allowed(self):
        redis, pipe = make_redis_mock(incr_return_value=100)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_request_uses_correct_redis_key(self):
        redis, pipe = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis)
        await limiter.check_rate_limit('my_identifier')
        pipe.incr.assert_called_once_with('rate_limit:send_notification:my_identifier')

    @pytest.mark.asyncio
    async def test_pipeline_called_with_transaction_true(self):
        redis, pipe = make_redis_mock(incr_return_value=1)
        limiter = make_limiter(redis)
        await limiter.check_rate_limit('user1')
        redis.pipeline.assert_called_once_with(transaction=True)


# ---------------------------------------------------------------------------
# check_rate_limit — limit exceeded
# ---------------------------------------------------------------------------

class TestCheckRateLimitExceeded:
    @pytest.mark.asyncio
    async def test_request_over_limit_rejected(self):
        redis, pipe = make_redis_mock(incr_return_value=101)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is False

    @pytest.mark.asyncio
    async def test_far_over_limit_rejected(self):
        redis, pipe = make_redis_mock(incr_return_value=999)
        limiter = make_limiter(redis, max_requests=100)
        result = await limiter.check_rate_limit('user1')
        assert result is False

    @pytest.mark.asyncio
    async def test_limit_is_per_identifier(self):
        """Different identifiers have independent counters (each starts fresh)."""
        redis_a, _ = make_redis_mock(incr_return_value=101)
        redis_b, _ = make_redis_mock(incr_return_value=1)
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
        redis, pipe = make_redis_mock(
            execute_side_effect=ConnectionError('refused')
        )
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_error_allows_request(self):
        redis, pipe = make_redis_mock(
            execute_side_effect=TimeoutError('timeout')
        )
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_generic_exception_allows_request(self):
        redis, pipe = make_redis_mock(
            execute_side_effect=Exception('unexpected')
        )
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_pipeline_creation_error_allows_request(self):
        """If pipeline() itself raises, request must be allowed through."""
        redis, _ = make_redis_mock(pipeline_side_effect=Exception('pipeline broken'))
        limiter = make_limiter(redis)
        result = await limiter.check_rate_limit('user1')
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_error_logs_warning(self, caplog):
        import logging
        redis, pipe = make_redis_mock(
            execute_side_effect=ConnectionError('down')
        )
        limiter = make_limiter(redis)
        with caplog.at_level(logging.WARNING):
            await limiter.check_rate_limit('user_x')
        assert any('user_x' in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# initialize / get_instance
# ---------------------------------------------------------------------------

class TestInitialize:
    def test_initialize_stores_instance(self):
        redis, _ = make_redis_mock()
        instance = RateLimiter.initialize(redis, 50, 30)
        assert RateLimiter.get_instance() is instance

    def test_get_instance_returns_none_before_initialize(self):
        RateLimiter._instance = None
        assert RateLimiter.get_instance() is None

    def test_initialize_sets_max_requests(self):
        redis, _ = make_redis_mock()
        instance = RateLimiter.initialize(redis, 42, 60)
        assert instance._max_requests == 42

    def test_initialize_sets_window(self):
        redis, _ = make_redis_mock()
        instance = RateLimiter.initialize(redis, 100, 120)
        assert instance._window_seconds == 120
