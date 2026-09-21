from __future__ import annotations

import json
from typing import Any


class RedisJsonCache:
    def __init__(self, redis: Any, *, prefix: str = "cache") -> None:
        self._redis = redis
        self._prefix = prefix

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(f"{self._prefix}:{key}")
        except Exception:
            return None
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        try:
            await self._redis.set(
                f"{self._prefix}:{key}",
                json.dumps(value, ensure_ascii=False),
                ex=ttl_seconds,
            )
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        try:
            return bool(await self._redis.delete(f"{self._prefix}:{key}"))
        except Exception:
            return False
