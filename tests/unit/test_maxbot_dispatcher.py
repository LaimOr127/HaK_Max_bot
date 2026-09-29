from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from navigator.application.checklists import ChecklistService
from navigator.application.dto import ChecklistDTO, MeasureDetailsDTO, RecommendationDTO
from navigator.application.onboarding import OnboardingService
from navigator.application.profiles import ProfileService
from navigator.application.recommendations import RecommendationService
from navigator.domain.entities import BusinessProfile, ChecklistDocumentState, UserMeasureChecklist
from navigator.domain.enums import (
    ConversationState,
    MatchStatus,
    ProfileSource,
)
from navigator.presentation.maxbot.dispatcher import (
    CallbackInteraction,
    MaxBotDispatcher,
    MaxBotServices,
    TextInteraction,
)


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
        self.values: dict[int, BusinessProfile] = {}
        self.deleted: list[int] = []

    async def get_by_user(self, max_user_id: int) -> BusinessProfile | None:
        return self.values.get(max_user_id)

    async def save(self, profile: BusinessProfile) -> None:
        self.values[profile.max_user_id] = profile

    async def delete_by_user(self, max_user_id: int) -> None:
        self.deleted.append(max_user_id)
        self.values.pop(max_user_id, None)


class FakeOnboarding(OnboardingService):
    def __init__(self, states: FakeStates, profiles: FakeProfiles) -> None:
        self.states = states
        self.profiles = profiles
        self.confirmed: list[int] = []

    async def start(self, max_user_id: int) -> None:
        await self.states.set_state(max_user_id, ConversationState.AWAITING_INN, {})

    async def start_manual(self, max_user_id: int) -> None:
        await self.states.set_state(max_user_id, ConversationState.MANUAL_REGION, {})

    async def lookup_inn(self, max_user_id: int, raw_inn: str) -> BusinessProfile:
        profile = BusinessProfile(
            max_user_id=max_user_id,
            inn=raw_inn,
            company_name="Demo LLC",
            source=ProfileSource.FNS,
        )
        await self.profiles.save(profile)
        await self.states.set_state(max_user_id, ConversationState.CONFIRM_PROFILE, {})
        return profile

    async def confirm_profile(self, max_user_id: int) -> BusinessProfile:
        self.confirmed.append(max_user_id)
        await self.states.set_state(max_user_id, ConversationState.READY, {})
        return self.profiles.values[max_user_id]


class FakeRecommendations(RecommendationService):
    def __init__(self, measure_id: UUID) -> None:
        self.measure_id = measure_id
        self.shown: list[int] = []

    async def recommend_for_user(
        self, max_user_id: int, limit: int = 3
    ) -> tuple[RecommendationDTO, ...]:
        self.shown.append(max_user_id)
        return (
            RecommendationDTO(
                self.measure_id,
                "Грант",
                "до 500 000 ₽",
                "regional",
                MatchStatus.ELIGIBLE,
                ("регион совпадает",),
            ),
        )

    async def get_details(self, max_user_id: int, measure_id: UUID) -> MeasureDetailsDTO:
        return MeasureDetailsDTO(
            measure_id,
            "Грант",
            "Деньги на запуск",
            "Малый бизнес",
            "до 500 000 ₽",
            None,
            ("Заявление", "Паспорт"),
            "Портал",
            10,
            None,
            "Источник",
            "https://example.com",
            date(2026, 9, 1),
        )


@dataclass
class FakeChecklistService(ChecklistService):
    measure_id: UUID
    document_id: UUID
    done: bool = False

    async def add_measure(self, max_user_id: int, measure_id: UUID) -> ChecklistDTO:
        return self._dto(max_user_id)

    async def list_checklists(self, max_user_id: int) -> ChecklistDTO:
        return self._dto(max_user_id)

    async def toggle_document(self, max_user_id: int, document_state_id: UUID) -> ChecklistDTO:
        self.done = not self.done
        return self._dto(max_user_id)

    def _dto(self, max_user_id: int) -> ChecklistDTO:
        return ChecklistDTO(
            (
                UserMeasureChecklist(
                    uuid4(),
                    max_user_id,
                    self.measure_id,
                    "Грант",
                    datetime.now(UTC),
                    (
                        ChecklistDocumentState(
                            self.document_id, uuid4(), "Заявление", is_done=self.done
                        ),
                    ),
                ),
            )
        )


@pytest.mark.asyncio
async def test_start_and_nav_start_show_onboarding_prompt() -> None:
    dispatcher = _dispatcher()

    started = await dispatcher.handle_text(TextInteraction(42, "/start"))
    prompted = await dispatcher.handle_callback(CallbackInteraction(42, "nav:start"))

    assert started[0].buttons[0][0].callback == "nav:start"
    assert "Введите ИНН" in prompted[0].text


@pytest.mark.asyncio
async def test_manual_onboarding_collects_fields_and_saves_profile() -> None:
    dispatcher = _dispatcher()

    await dispatcher.handle_callback(CallbackInteraction(42, "inn:manual"))
    await dispatcher.handle_text(TextInteraction(42, "Москва"))
    await dispatcher.handle_callback(CallbackInteraction(42, "business_form:ip"))
    await dispatcher.handle_callback(CallbackInteraction(42, "sphere:it"))
    await dispatcher.handle_callback(CallbackInteraction(42, "stage:lt1"))
    result = await dispatcher.handle_callback(CallbackInteraction(42, "employees:2_15"))

    assert "Проверьте профиль" in result[0].text
    assert "Москва" in result[0].text
    assert result[0].buttons[0][0].callback == "profile:confirm"


@pytest.mark.asyncio
async def test_confirm_profile_returns_recommendation_card() -> None:
    dispatcher = _dispatcher()

    await dispatcher.handle_callback(CallbackInteraction(42, "inn:manual"))
    await dispatcher.handle_text(TextInteraction(42, "Москва"))
    await dispatcher.handle_callback(CallbackInteraction(42, "business_form:ip"))
    await dispatcher.handle_callback(CallbackInteraction(42, "sphere:it"))
    await dispatcher.handle_callback(CallbackInteraction(42, "stage:lt1"))
    await dispatcher.handle_callback(CallbackInteraction(42, "employees:2_15"))
    result = await dispatcher.handle_callback(CallbackInteraction(42, "profile:confirm"))

    assert "Грант" in result[0].text
    assert result[0].buttons[0][0].callback.startswith("measure:details:")


@pytest.mark.asyncio
async def test_details_add_and_toggle_document() -> None:
    measure_id = uuid4()
    document_id = uuid4()
    dispatcher = _dispatcher(measure_id, document_id)

    details = await dispatcher.handle_callback(
        CallbackInteraction(42, f"measure:details:{measure_id}")
    )
    checklist = await dispatcher.handle_callback(
        CallbackInteraction(42, f"measure:add:{measure_id}")
    )
    toggled = await dispatcher.handle_callback(
        CallbackInteraction(42, f"document:toggle:{document_id}")
    )

    assert "Деньги на запуск" in details[0].text
    assert "Заявление" in checklist[0].text
    assert "Заявление" in toggled[0].text
    assert "готово" in toggled[0].text


def _dispatcher(
    measure_id: UUID | None = None, document_id: UUID | None = None
) -> MaxBotDispatcher:
    measure_id = measure_id or uuid4()
    document_id = document_id or uuid4()
    states = FakeStates()
    profiles = FakeProfiles()
    return MaxBotDispatcher(
        MaxBotServices(
            states=states,
            onboarding=FakeOnboarding(states, profiles),
            profiles=ProfileService(profiles),
            recommendations=FakeRecommendations(measure_id),
            checklists=FakeChecklistService(measure_id, document_id),
        )
    )
