from __future__ import annotations

from typing import Protocol

from navigator.domain.entities import BusinessProfile, Measure


class ExplanationProvider(Protocol):
    async def explain_match(
        self, profile: BusinessProfile, measure: Measure, reasons: tuple[str, ...]
    ) -> str: ...
