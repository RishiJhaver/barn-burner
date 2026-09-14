"""Unit and integration tests for Redis-backed sliding-window rate limiter."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.config import get_settings
from app.core.rate_limiter import RateLimiter
from app.main import app

settings = get_settings()


async def get_test_headers(client: AsyncClient, username: str) -> dict:
    sub = f"sub-{username}-{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/v1/auth/demo-token",
        json={
            "sub": sub,
            "email": f"{username}@example.com",
            "username": username,
            "role": "user",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio(loop_scope="function")
async def test_rate_limiter_allows_under_limit(client):
    """Ensure requests under the rate limit succeed."""
    uid = uuid.uuid4().hex[:6]
    headers = await get_test_headers(client, f"rl_user_{uid}")

    # Use low limit test instance
    limiter = RateLimiter(action=f"test_allow_{uid}", limit=5, window_seconds=10)

    # Test via direct call simulation
    class FakeUser:
        id = uuid.uuid4()

    fake_user = FakeUser()
    for _ in range(5):
        await limiter(request=None, current_user=fake_user)


@pytest.mark.asyncio(loop_scope="function")
async def test_rate_limiter_blocks_over_limit(client):
    """Ensure requests exceeding limit return HTTP 429 with Retry-After header."""
    # Check if Redis is reachable
    from app.services.cache_service import get_redis_client
    redis_client = get_redis_client()
    try:
        await redis_client.ping()
    except Exception:
        pytest.skip("Redis server is not running locally; skipping live rate limiter test.")

    uid = uuid.uuid4().hex[:6]
    limiter = RateLimiter(action=f"test_block_{uid}", limit=2, window_seconds=5)

    class FakeUser:
        id = uuid.uuid4()

    fake_user = FakeUser()

    # First 2 should pass
    await limiter(request=None, current_user=fake_user)
    await limiter(request=None, current_user=fake_user)

    # 3rd should raise 429
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request=None, current_user=fake_user)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers
    assert int(exc_info.value.headers["Retry-After"]) >= 1


@pytest.mark.asyncio(loop_scope="function")
async def test_rate_limiter_bypass_when_disabled():
    """Ensure rate limiter passes through cleanly when disabled."""
    original = settings.RATE_LIMIT_ENABLED
    try:
        settings.RATE_LIMIT_ENABLED = False
        limiter = RateLimiter(action="disabled_test", limit=1, window_seconds=10)

        class FakeUser:
            id = uuid.uuid4()

        fake_user = FakeUser()
        # Should allow multiple even if limit=1
        await limiter(request=None, current_user=fake_user)
        await limiter(request=None, current_user=fake_user)
    finally:
        settings.RATE_LIMIT_ENABLED = original


@pytest.mark.asyncio(loop_scope="function")
async def test_rate_limiter_fail_open_on_redis_error(monkeypatch):
    """Ensure rate limiter fails open without throwing errors if Redis raises an unexpected exception."""
    from unittest.mock import MagicMock
    mock_redis = MagicMock()
    mock_redis.pipeline.side_effect = ConnectionError("Redis connection dropped")

    import app.core.rate_limiter as rl_module
    monkeypatch.setattr(rl_module, "get_redis_client", lambda: mock_redis)

    limiter = RateLimiter(action="fail_open_test", limit=1, window_seconds=10)

    class FakeUser:
        id = uuid.uuid4()

    fake_user = FakeUser()
    # Should not raise exception even though Redis errored
    await limiter(request=None, current_user=fake_user)

