from __future__ import annotations

from typing import Protocol


class RateLimiter(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> bool: ...
