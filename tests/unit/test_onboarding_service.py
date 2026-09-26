from datetime import UTC, datetime

import pytest

from navigator.application.onboarding import OnboardingService
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
from navigator.domain.errors import CompanyNotFound
from navigator.ports.company_lookup import CompanyLookupResult


class FakeStates:
    def __init__(self) -> None:
        self.values: dict[int, tuple[ConversationState, dict[str, object]]] = {}

    async def get_state(
        self, max_user_id: int
    ) -> tuple[ConversationState, dict[str, object]] | None:
        return self.values.get(max_user_id)

    async def set_state(
        self, max_user_id: int, state: ConversationState, context: dict[str, object] | None = None
    ) -> None:
        self.values[max_user_id] = (state, context or {})


class FakeProfiles:
    def __init__(self) -> None:
        self.values = {}

    async def get_by_user(self, max_user_id: int):
        return self.values.get(max_user_id)

    async def save(self, profile) -> None:
        self.values[profile.max_user_id] = profile

    async def delete_by_user(self, max_user_id: int) -> None:
        self.values.pop(max_user_id, None)


class FakeLookup:
    def __init__(self, result: CompanyLookupResult) -> None:
        self.result = result
        self.requested: list[str] = []

    async def find_by_inn(self, inn: str) -> CompanyLookupResult:
        self.requested.append(inn)
        return self.result


class FakeAnalytics:
    def __init__(self) -> None:
        self.events: list[AnalyticsEventType] = []

    async def track(self, event_type, max_user_id=None, measure_id=None, properties=None) -> None:
        self.events.append(event_type)


@pytest.mark.asyncio
async def test_start_moves_user_to_waiting_for_inn() -> None:
    states = FakeStates()
    analytics = FakeAnalytics()

    await OnboardingService(states, FakeProfiles(), FakeLookup(_not_found()), analytics).start(42)

    assert states.values[42] == (ConversationState.AWAITING_INN, {})
    assert analytics.events == [AnalyticsEventType.ONBOARDING_STARTED]


@pytest.mark.asyncio
async def test_lookup_inn_saves_fns_profile_and_waits_for_confirmation() -> None:
    checked_at = datetime(2026, 9, 1, tzinfo=UTC)
    states = FakeStates()
    profiles = FakeProfiles()
    lookup = FakeLookup(
        CompanyLookupResult(
            status=CompanyLookupStatus.FOUND,
            inn="7707083893",
            company_name="Demo LLC",
            business_form=BusinessForm.OOO,
            region_code="77",
            primary_okved="62.01",
            employee_count=12,
            source_checked_at=checked_at,
        )
    )

    profile = await OnboardingService(states, profiles, lookup).lookup_inn(42, "77 07083893")

    assert lookup.requested == ["7707083893"]
    assert profile.source is ProfileSource.FNS
    assert profile.sphere is SphereCategory.IT_DIGITAL
    assert profile.employee_bucket is EmployeeBucket.TWO_TO_FIFTEEN
    assert profile.fns_checked_at == checked_at
    assert profiles.values[42] == profile
    assert states.values[42] == (
        ConversationState.CONFIRM_PROFILE,
        {"current_inn": "7707083893"},
    )


@pytest.mark.asyncio
async def test_lookup_inn_tracks_not_found_without_saving_profile() -> None:
    profiles = FakeProfiles()
    analytics = FakeAnalytics()

    with pytest.raises(CompanyNotFound):
        await OnboardingService(
            FakeStates(), profiles, FakeLookup(_not_found()), analytics
        ).lookup_inn(42, "7707083893")

    assert profiles.values == {}
    assert analytics.events == [
        AnalyticsEventType.INN_LOOKUP_STARTED,
        AnalyticsEventType.INN_LOOKUP_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_repeat_lookup_preserves_answers_for_same_inn() -> None:
    profiles = FakeProfiles()
    profiles.values[42] = BusinessProfile(
        max_user_id=42,
        inn="7707083893",
        sphere=SphereCategory.IT_DIGITAL,
        business_stage=BusinessStage.GT3,
        employee_bucket=EmployeeBucket.SIXTEEN_TO_HUNDRED,
    )
    lookup = FakeLookup(CompanyLookupResult(status=CompanyLookupStatus.FOUND, inn="7707083893"))

    profile = await OnboardingService(FakeStates(), profiles, lookup).lookup_inn(42, "7707083893")

    assert profile.sphere is SphereCategory.IT_DIGITAL
    assert profile.business_stage is BusinessStage.GT3
    assert profile.employee_bucket is EmployeeBucket.SIXTEEN_TO_HUNDRED


def _not_found() -> CompanyLookupResult:
    return CompanyLookupResult(status=CompanyLookupStatus.NOT_FOUND, inn="7707083893")
