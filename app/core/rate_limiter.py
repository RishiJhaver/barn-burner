"""Redis-backed Sliding-Window Rate Limiter dependency for FastAPI."""

import logging
import time
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.services.cache_service import get_redis_client

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """
    Sliding-window rate limiter using Redis Sorted Sets (ZSET).
    Enforces short-window anti-spam limits per authenticated user.
    """

    def __init__(
        self,
        action: str = "code_execution",
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ):
        self.action = action
        self.limit = limit if limit is not None else settings.RATE_LIMIT_RUN_PER_MINUTE
        self.window_seconds = window_seconds if window_seconds is not None else settings.RATE_LIMIT_WINDOW_SECONDS

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        user_id = str(current_user.id)
        key = f"rate_limit:{self.action}:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        try:
            redis_client = get_redis_client()
            pipe = redis_client.pipeline()
            # 1. Purge requests outside current sliding window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Count requests in active window
            pipe.zcard(key)
            # 3. Get oldest request in window for precise Retry-After header
            pipe.zrange(key, 0, 0, withscores=True)
            results = await pipe.execute()

            current_count = results[1]
            oldest_items = results[2]

            if current_count >= self.limit:
                retry_after = self.window_seconds
                if oldest_items:
                    oldest_ts = oldest_items[0][1]
                    retry_after = max(1, int(self.window_seconds - (now - oldest_ts)))

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: maximum {self.limit} executions per {self.window_seconds} seconds. Please wait before retrying.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                    },
                )

            # 4. Record new request with unique member timestamp
            member = f"{now}:{uuid.uuid4().hex[:6]}"
            add_pipe = redis_client.pipeline()
            add_pipe.zadd(key, {member: now})
            add_pipe.expire(key, self.window_seconds + 10)
            await add_pipe.execute()

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Redis rate limiter encountered an issue; failing open: %s", e)
            return
