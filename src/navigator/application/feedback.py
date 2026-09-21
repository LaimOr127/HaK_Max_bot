from __future__ import annotations

from navigator.domain.entities import Feedback
from navigator.domain.enums import AnalyticsEventType
from navigator.ports.repositories import AnalyticsRepository, FeedbackRepository

from .dto import FeedbackInput


class FeedbackService:
    def __init__(
        self, feedback: FeedbackRepository, analytics: AnalyticsRepository | None = None
    ) -> None:
        self._feedback = feedback
        self._analytics = analytics

    async def submit(self, data: FeedbackInput) -> None:
        await self._feedback.add(
            Feedback(data.max_user_id, data.measure_id, data.feedback_type, data.comment)
        )
        if self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.FEEDBACK_SUBMITTED,
                max_user_id=data.max_user_id,
                measure_id=data.measure_id,
                properties={"type": data.feedback_type.value},
            )
