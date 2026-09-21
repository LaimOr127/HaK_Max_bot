from __future__ import annotations

from navigator.domain.entities import InvestorLead
from navigator.domain.enums import AnalyticsEventType, InvestorPromptState
from navigator.ports.repositories import AnalyticsRepository, InvestorRepository

from .dto import InvestorLeadInput


class InvestorService:
    def __init__(
        self, investors: InvestorRepository, analytics: AnalyticsRepository | None = None
    ) -> None:
        self._investors = investors
        self._analytics = analytics

    async def should_prompt(self, max_user_id: int) -> bool:
        return await self._investors.get_prompt_state(max_user_id) is InvestorPromptState.NOT_SHOWN

    async def decline(self, max_user_id: int) -> None:
        await self._investors.set_prompt_state(max_user_id, InvestorPromptState.DECLINED)

    async def submit_interest(self, data: InvestorLeadInput) -> bool:
        created = await self._investors.add_lead(
            InvestorLead(data.max_user_id, data.name, data.contact)
        )
        await self._investors.set_prompt_state(data.max_user_id, InvestorPromptState.INTERESTED)
        if created and self._analytics is not None:
            await self._analytics.track(
                AnalyticsEventType.INVESTOR_INTEREST_SUBMITTED, max_user_id=data.max_user_id
            )
        return created
