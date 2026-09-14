"""Redis async cache service with pattern invalidation and graceful fallback."""

import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None
_redis_loop = None


def get_redis_client() -> aioredis.Redis:
    """Return async Redis client scoped to the current event loop."""
    global _redis_client, _redis_loop
    import asyncio

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _redis_client is None or _redis_loop != current_loop:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        _redis_loop = current_loop
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class CacheService:
    """Async Redis caching operations with safe degradation."""

    @staticmethod
    async def get(key: str) -> Optional[str]:
        try:
            client = get_redis_client()
            return await client.get(key)
        except Exception as exc:
            logger.warning("Redis GET failed for key %s: %s", key, exc)
            return None

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        data = await CacheService.get(key)
        if data:
            try:
                return json.loads(data)
            except Exception as exc:
                logger.warning("Failed to decode JSON from cache for key %s: %s", key, exc)
        return None

    @staticmethod
    async def set(key: str, value: str, ttl: int = 60) -> bool:
        try:
            client = get_redis_client()
            await client.set(key, value, ex=ttl)
            return True
        except Exception as exc:
            logger.warning("Redis SET failed for key %s: %s", key, exc)
            return False

    @staticmethod
    async def set_json(key: str, value: Any, ttl: int = 60) -> bool:
        try:
            dumped = json.dumps(value, default=str)
            return await CacheService.set(key, dumped, ttl=ttl)
        except Exception as exc:
            logger.warning("Failed to encode JSON to cache for key %s: %s", key, exc)
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        try:
            client = get_redis_client()
            await client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Redis DELETE failed for key %s: %s", key, exc)
            return False

    @staticmethod
    async def invalidate_pattern(pattern: str) -> int:
        """Scan and delete all keys matching pattern."""
        try:
            client = get_redis_client()
            keys_to_delete = []
            async for k in client.scan_iter(match=pattern):
                keys_to_delete.append(k)
            if keys_to_delete:
                await client.delete(*keys_to_delete)
            return len(keys_to_delete)
        except Exception as exc:
            logger.warning("Redis invalidate_pattern failed for pattern %s: %s", pattern, exc)
            return 0

    # Specialized Problem Cache Helpers
    @staticmethod
    def problem_list_key(
        last_id: Optional[int] = None,
        limit: int = 20,
        difficulty: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> str:
        return f"problems:list:diff={difficulty}:tag={tag}:last={last_id}:limit={limit}"

    @staticmethod
    def problem_detail_key(slug: str) -> str:
        return f"problems:detail:{slug}"

    @classmethod
    async def invalidate_problem_cache(cls, slug: Optional[str] = None) -> None:
        """Invalidates all list pages and optionally a specific problem detail."""
        await cls.invalidate_pattern("problems:list:*")
        if slug:
            await cls.delete(cls.problem_detail_key(slug))
