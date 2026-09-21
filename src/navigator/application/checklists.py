from __future__ import annotations

from uuid import UUID

from navigator.domain.enums import AnalyticsEventType
from navigator.domain.errors import MeasureNotFound
from navigator.ports.repositories import AnalyticsRepository, ChecklistRepository, MeasureRepository

from .dto import ChecklistDTO


class ChecklistService:
    def __init__(
        self,
        checklists: ChecklistRepository,
        measures: MeasureRepository,
        analytics: AnalyticsRepository | None = None,
    ) -> None:
        self._checklists = checklists
        self._measures = measures
        self._analytics = analytics

    async def add_measure(self, max_user_id: int, measure_id: UUID) -> ChecklistDTO:
        measure = await self._measures.get(measure_id)
        if measure is None:
            raise MeasureNotFound(str(measure_id))
        _, created = await self._checklists.add_measure(max_user_id, measure)
        if created and self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.CHECKLIST_ADDED, max_user_id=max_user_id, measure_id=measure_id
            )
        return await self.list_checklists(max_user_id)

    async def list_checklists(self, max_user_id: int) -> ChecklistDTO:
        return ChecklistDTO(tuple(await self._checklists.list_by_user(max_user_id)))

    async def toggle_document(self, max_user_id: int, document_state_id: UUID) -> ChecklistDTO:
        checklist = await self._checklists.toggle_document(max_user_id, document_state_id)
        if self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.CHECKLIST_DOCUMENT_DONE,
                max_user_id=max_user_id,
                measure_id=checklist.measure_id,
            )
        return await self.list_checklists(max_user_id)

    async def remove_measure(self, max_user_id: int, measure_id: UUID) -> ChecklistDTO:
        await self._checklists.remove_measure(max_user_id, measure_id)
        return await self.list_checklists(max_user_id)
