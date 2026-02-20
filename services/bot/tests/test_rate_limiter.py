import pytest
from unittest.mock import AsyncMock, MagicMock

from app.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_check_rate_limit_primer_request_setea_ttl(mocker):
    redis_mock = MagicMock()
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    mocker.patch("app.rate_limiter.Redis.from_url", return_value=redis_mock)

    limiter = RateLimiter("redis://localhost:6379/0", max_requests=10, window_seconds=60)
    is_allowed, current_count, limit = await limiter.check_rate_limit("521111111111")

    assert is_allowed is True
    assert current_count == 1
    assert limit == 10
    redis_mock.incr.assert_awaited_once_with("ratelimit:521111111111")
    redis_mock.expire.assert_awaited_once_with("ratelimit:521111111111", 60)


@pytest.mark.asyncio
async def test_check_rate_limit_en_limite_permite(mocker):
    redis_mock = MagicMock()
    redis_mock.incr = AsyncMock(return_value=10)
    redis_mock.expire = AsyncMock(return_value=True)
    mocker.patch("app.rate_limiter.Redis.from_url", return_value=redis_mock)

    limiter = RateLimiter("redis://localhost:6379/0", max_requests=10, window_seconds=60)
    is_allowed, current_count, limit = await limiter.check_rate_limit("521111111111")

    assert is_allowed is True
    assert current_count == 10
    assert limit == 10
    redis_mock.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_rate_limit_excedido_bloquea(mocker):
    redis_mock = MagicMock()
    redis_mock.incr = AsyncMock(return_value=11)
    redis_mock.expire = AsyncMock(return_value=True)
    mocker.patch("app.rate_limiter.Redis.from_url", return_value=redis_mock)

    limiter = RateLimiter("redis://localhost:6379/0", max_requests=10, window_seconds=60)
    is_allowed, current_count, limit = await limiter.check_rate_limit("521111111111")

    assert is_allowed is False
    assert current_count == 11
    assert limit == 10


@pytest.mark.asyncio
async def test_check_rate_limit_falla_redis_fail_open(mocker):
    redis_mock = MagicMock()
    redis_mock.incr = AsyncMock(side_effect=RuntimeError("redis down"))
    redis_mock.expire = AsyncMock(return_value=True)
    mocker.patch("app.rate_limiter.Redis.from_url", return_value=redis_mock)

    limiter = RateLimiter("redis://localhost:6379/0", max_requests=10, window_seconds=60)
    is_allowed, current_count, limit = await limiter.check_rate_limit("521111111111")

    assert is_allowed is True
    assert current_count == 0
    assert limit == 10
    redis_mock.expire.assert_not_awaited()
