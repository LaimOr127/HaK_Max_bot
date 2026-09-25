from __future__ import annotations

from datetime import UTC, datetime

from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    AnalyticsEventType,
    BusinessForm,
    BusinessStage,
    CompanyLookupStatus,
    ConversationState,
    EmployeeBucket,
    ProfileSource,
    SphereCategory,
)
from navigator.domain.errors import CompanyLookupUnavailable, CompanyNotFound
from navigator.domain.inn import normalize_inn
from navigator.ports.company_lookup import CompanyLookup
from navigator.ports.repositories import (
    AnalyticsRepository,
    ConversationStateRepository,
    ProfileRepository,
)


class OnboardingService:
    def __init__(
        self,
        states: ConversationStateRepository,
        profiles: ProfileRepository,
        company_lookup: CompanyLookup,
        analytics: AnalyticsRepository | None = None,
    ) -> None:
        self._states = states
        self._profiles = profiles
        self._company_lookup = company_lookup
        self._analytics = analytics

    async def start(self, max_user_id: int) -> None:
        await self._states.set_state(max_user_id, ConversationState.AWAITING_INN, {})
        await self._track(AnalyticsEventType.ONBOARDING_STARTED, max_user_id)

    async def start_manual(self, max_user_id: int) -> None:
        await self._states.set_state(max_user_id, ConversationState.MANUAL_REGION, {})
        await self._track(AnalyticsEventType.MANUAL_ONBOARDING_STARTED, max_user_id)

    async def set_manual_region(self, max_user_id: int, region: str) -> None:
        _, context = await self._state_context(max_user_id)
        context["region_code"] = normalize_region(region)
        await self._states.set_state(max_user_id, ConversationState.MANUAL_BUSINESS_FORM, context)

    async def set_manual_form(self, max_user_id: int, value: str) -> None:
        _, context = await self._state_context(max_user_id)
        context["business_form"] = BusinessForm(value).value
        await self._states.set_state(max_user_id, ConversationState.MANUAL_SPHERE, context)

    async def set_manual_sphere(self, max_user_id: int, value: str) -> None:
        _, context = await self._state_context(max_user_id)
        context["sphere"] = SphereCategory(value).value
        await self._states.set_state(max_user_id, ConversationState.MANUAL_STAGE, context)

    async def set_manual_stage(self, max_user_id: int, value: str) -> None:
        _, context = await self._state_context(max_user_id)
        context["business_stage"] = BusinessStage(value).value
        await self._states.set_state(max_user_id, ConversationState.MANUAL_EMPLOYEES, context)

    async def finish_manual(self, max_user_id: int, value: str) -> BusinessProfile:
        _, context = await self._state_context(max_user_id)
        context["employee_bucket"] = EmployeeBucket(value).value
        try:
            profile = BusinessProfile(
                max_user_id=max_user_id,
                region_code=str(context["region_code"]),
                business_form=BusinessForm(str(context["business_form"])),
                sphere=SphereCategory(str(context["sphere"])),
                business_stage=BusinessStage(str(context["business_stage"])),
                employee_bucket=EmployeeBucket(str(context["employee_bucket"])),
                source=ProfileSource.MANUAL,
                consent_at=datetime.now(UTC),
            )
        except KeyError as exc:
            raise CompanyNotFound("profile draft") from exc
        await self._profiles.save(profile)
        await self._states.set_state(max_user_id, ConversationState.CONFIRM_PROFILE, {})
        return profile

    async def lookup_inn(self, max_user_id: int, raw_inn: str) -> BusinessProfile:
        inn = normalize_inn(raw_inn)
        await self._track(AnalyticsEventType.INN_LOOKUP_STARTED, max_user_id)
        result = await self._company_lookup.find_by_inn(inn)
        if result.status is CompanyLookupStatus.NOT_FOUND:
            await self._track(AnalyticsEventType.INN_LOOKUP_NOT_FOUND, max_user_id)
            raise CompanyNotFound(inn)
        if result.status is CompanyLookupStatus.TEMPORARILY_UNAVAILABLE:
            await self._track(AnalyticsEventType.INN_LOOKUP_FAILED, max_user_id)
            raise CompanyLookupUnavailable(inn)

        previous = await self._profiles.get_by_user(max_user_id)
        same_company = previous if previous is not None and previous.inn == inn else None
        profile = BusinessProfile(
            max_user_id=max_user_id,
            inn=inn,
            company_name=result.company_name,
            region_code=result.region_code,
            primary_okved=result.primary_okved,
            business_form=result.business_form or _form_from_inn(inn),
            sphere=same_company.sphere if same_company else None,
            business_stage=same_company.business_stage if same_company else None,
            employee_bucket=(
                _bucket_from_count(result.employee_count)
                or (same_company.employee_bucket if same_company else None)
            ),
            employee_count=result.employee_count
            or (same_company.employee_count if same_company else None),
            msp_category=result.msp_category,
            source=ProfileSource.FNS,
            fns_checked_at=result.source_checked_at or datetime.now(UTC),
        )
        await self._profiles.save(profile)
        await self._states.set_state(
            max_user_id, ConversationState.CONFIRM_PROFILE, {"current_inn": inn}
        )
        await self._track(AnalyticsEventType.INN_LOOKUP_SUCCESS, max_user_id)
        return profile

    async def confirm_profile(self, max_user_id: int) -> BusinessProfile:
        profile = await self._profiles.get_by_user(max_user_id)
        if profile is None:
            raise CompanyNotFound("profile")
        await self._states.set_state(max_user_id, ConversationState.READY, {})
        await self._track(AnalyticsEventType.PROFILE_CONFIRMED, max_user_id)
        return profile

    async def reset_user_data(self, max_user_id: int) -> None:
        await self._profiles.delete_by_user(max_user_id)
        await self._states.set_state(max_user_id, ConversationState.IDLE, {})

    async def _state_context(self, max_user_id: int) -> tuple[ConversationState, dict[str, object]]:
        stored = await self._states.get_state(max_user_id)
        if stored is None:
            return ConversationState.IDLE, {}
        state, context = stored
        return state, dict(context)

    async def _track(self, event_type: AnalyticsEventType, max_user_id: int) -> None:
        if self._analytics is not None:
            await self._analytics.track(event_type, max_user_id=max_user_id)


def _form_from_inn(inn: str) -> BusinessForm:
    return BusinessForm.OOO if len(inn) == 10 else BusinessForm.IP


def _bucket_from_count(count: int | None) -> EmployeeBucket | None:
    if count is None:
        return None
    if count <= 1:
        return EmployeeBucket.ONE
    if count <= 15:
        return EmployeeBucket.TWO_TO_FIFTEEN
    if count <= 100:
        return EmployeeBucket.SIXTEEN_TO_HUNDRED
    return EmployeeBucket.OVER_HUNDRED


_REGIONS = {
    "москва": "77",
    "московская область": "50",
    "санкт-петербург": "78",
    "санкт петербург": "78",
    "татарстан": "16",
    "республика татарстан": "16",
}


def normalize_region(value: str) -> str:
    cleaned = " ".join(value.strip().lower().replace("ё", "е").split())
    return _REGIONS.get(cleaned, value.strip()[:16] or "77")
