from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from navigator.domain.entities import (
    BusinessProfile,
    Feedback,
    InvestorLead,
    Measure,
    UserMeasureChecklist,
)
from navigator.domain.enums import AnalyticsEventType, ConversationState, InvestorPromptState


class UnitOfWork(Protocol):
    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    async def commit(self) -> None: ...


class ProfileRepository(Protocol):
    async def get_by_user(self, max_user_id: int) -> BusinessProfile | None: ...

    async def save(self, profile: BusinessProfile) -> None: ...

    async def delete_by_user(self, max_user_id: int) -> None: ...


class ConversationStateRepository(Protocol):
    async def get_state(
        self, max_user_id: int
    ) -> tuple[ConversationState, dict[str, object]] | None: ...

    async def set_state(
        self, max_user_id: int, state: ConversationState, context: dict[str, object] | None = None
    ) -> None: ...


class MeasureRepository(Protocol):
    async def list_active_candidates(self, today: date) -> list[Measure]: ...

    async def get(self, measure_id: UUID) -> Measure | None: ...


class ChecklistRepository(Protocol):
    async def add_measure(
        self, max_user_id: int, measure: Measure
    ) -> tuple[UserMeasureChecklist, bool]: ...

    async def list_by_user(self, max_user_id: int) -> list[UserMeasureChecklist]: ...

    async def toggle_document(
        self, max_user_id: int, document_state_id: UUID
    ) -> UserMeasureChecklist: ...

    async def remove_measure(self, max_user_id: int, measure_id: UUID) -> None: ...


class FeedbackRepository(Protocol):
    async def add(self, feedback: Feedback) -> None: ...


class InvestorRepository(Protocol):
    async def get_prompt_state(self, max_user_id: int) -> InvestorPromptState: ...

    async def set_prompt_state(self, max_user_id: int, state: InvestorPromptState) -> None: ...

    async def add_lead(self, lead: InvestorLead) -> bool: ...


class ReminderRepository(Protocol):
    async def due_checklists(self, today: date, days_before: int) -> list[UserMeasureChecklist]: ...

    async def mark_sent(self, max_user_id: int, measure_id: UUID, days_before: int) -> bool: ...


class AnalyticsRepository(Protocol):
    async def track(
        self,
        event_type: AnalyticsEventType,
        max_user_id: int | None = None,
        measure_id: UUID | None = None,
        properties: dict[str, object] | None = None,
    ) -> None: ...
