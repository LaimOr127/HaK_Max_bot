from __future__ import annotations

from uuid import UUID

from navigator.domain.enums import AnalyticsEventType
from navigator.ports.repositories import AnalyticsRepository


class AnalyticsService:
    def __init__(self, analytics: AnalyticsRepository) -> None:
        self._analytics = analytics

    async def track(
        self,
        event_type: AnalyticsEventType,
        max_user_id: int | None = None,
        measure_id: UUID | None = None,
        properties: dict[str, object] | None = None,
    ) -> None:
        await self._analytics.track(event_type, max_user_id, measure_id, properties)
