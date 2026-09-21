from __future__ import annotations

from typing import Any


class RedisRateLimiter:
    def __init__(self, redis: Any, *, prefix: str = "rl") -> None:
        self._redis = redis
        self._prefix = prefix

    async def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        redis_key = f"{self._prefix}:{key}"
        try:
            count = await self._redis.incr(redis_key)
            if count == 1:
                await self._redis.expire(redis_key, window_seconds)
            return int(count) <= limit
        except Exception:
            return True
