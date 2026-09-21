from __future__ import annotations

from typing import Any


class RedisIdempotencyStore:
    def __init__(self, redis: Any, *, prefix: str = "idem") -> None:
        self._redis = redis
        self._prefix = prefix

    async def mark_once(self, key: str, ttl_seconds: int) -> bool:
        return bool(
            await self._redis.set(
                f"{self._prefix}:{key}",
                "1",
                ex=ttl_seconds,
                nx=True,
            )
        )

    async def release(self, key: str) -> None:
        await self._redis.delete(f"{self._prefix}:{key}")
