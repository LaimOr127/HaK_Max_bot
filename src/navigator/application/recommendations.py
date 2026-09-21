from __future__ import annotations

from uuid import UUID

from navigator.domain.enums import AnalyticsEventType
from navigator.domain.errors import MeasureNotFound, ProfileIncomplete
from navigator.domain.matching import recommend
from navigator.ports.clock import Clock
from navigator.ports.repositories import AnalyticsRepository, MeasureRepository, ProfileRepository

from .dto import MeasureDetailsDTO, RecommendationDTO


class RecommendationService:
    def __init__(
        self,
        profiles: ProfileRepository,
        measures: MeasureRepository,
        clock: Clock,
        analytics: AnalyticsRepository | None = None,
    ) -> None:
        self._profiles = profiles
        self._measures = measures
        self._clock = clock
        self._analytics = analytics

    async def recommend_for_user(
        self, max_user_id: int, limit: int = 3
    ) -> tuple[RecommendationDTO, ...]:
        profile = await self._profiles.get_by_user(max_user_id)
        if profile is None:
            raise ProfileIncomplete("profile is required before recommendations")
        results = recommend(
            profile,
            await self._measures.list_active_candidates(self._clock.today()),
            self._clock.today(),
            limit,
        )
        if self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.RECOMMENDATIONS_SHOWN
                if results
                else AnalyticsEventType.ZERO_RECOMMENDATIONS,
                max_user_id=max_user_id,
                properties={"count": len(results)},
            )
        return tuple(
            RecommendationDTO(
                measure_id=result.measure.id,
                name=result.measure.name,
                amount_display=result.measure.amount_display,
                support_level=result.measure.support_level.value,
                status=result.status,
                reasons=result.reasons,
            )
            for result in results
        )

    async def get_details(self, max_user_id: int, measure_id: UUID) -> MeasureDetailsDTO:
        measure = await self._measures.get(measure_id)
        if measure is None:
            raise MeasureNotFound(str(measure_id))
        if self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.MEASURE_DETAILS_OPENED,
                max_user_id=max_user_id,
                measure_id=measure_id,
            )
        return MeasureDetailsDTO(
            measure_id=measure.id,
            name=measure.name,
            what_is_it=measure.what_is_it,
            who_can_receive=measure.who_can_receive,
            amount_display=measure.amount_display,
            benefit_detail=measure.benefit_detail,
            documents=tuple(
                document.title
                for document in sorted(measure.documents, key=lambda item: item.sort_order)
            ),
            where_to_apply=measure.where_to_apply,
            review_days=measure.review_days,
            application_deadline=measure.application_deadline,
            source_name=measure.source_name,
            source_url=measure.source_url,
            source_checked_at=measure.source_checked_at,
        )
