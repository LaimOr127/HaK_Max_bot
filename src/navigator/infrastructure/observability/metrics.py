from __future__ import annotations

from time import perf_counter


def monotonic_ms() -> int:
    return round(perf_counter() * 1000)
