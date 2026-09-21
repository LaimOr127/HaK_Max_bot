from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from navigator.application.checklists import ChecklistService
from navigator.application.dto import ProfileInput
from navigator.application.onboarding import OnboardingService
from navigator.application.profiles import ProfileService
from navigator.application.recommendations import RecommendationService
from navigator.domain.enums import ConversationState, MatchStatus
from navigator.domain.errors import (
    CompanyLookupUnavailable,
    CompanyNotFound,
    InvalidInn,
    MeasureNotFound,
    ProfileIncomplete,
)
from navigator.ports.max_gateway import Button, OutgoingMessage
from navigator.ports.repositories import ConversationStateRepository

from . import keyboards, messages
from .callbacks import Callback, InvalidCallback, parse_callback
from .renderers import render_measure, render_measure_details, render_profile


class InvestorPrompts(Protocol):
    async def should_prompt(self, max_user_id: int) -> bool: ...

    async def decline(self, max_user_id: int) -> None: ...


@dataclass(frozen=True, slots=True)
class TextInteraction:
    max_user_id: int
    text: str


@dataclass(frozen=True, slots=True)
class CallbackInteraction:
    max_user_id: int
    payload: str


@dataclass(frozen=True, slots=True)
class MaxBotServices:
    states: ConversationStateRepository
    onboarding: OnboardingService
    profiles: ProfileService
    recommendations: RecommendationService
    checklists: ChecklistService
    investors: InvestorPrompts | None = None


class MaxBotDispatcher:
    def __init__(self, services: MaxBotServices) -> None:
        self._services = services

    async def handle_text(self, interaction: TextInteraction) -> tuple[OutgoingMessage, ...]:
        text = interaction.text.strip()
        command = text.split(maxsplit=1)[0].lower()
        if command == "/start":
            return await self._start(interaction.max_user_id)
        if command == "/help":
            return (_message(interaction.max_user_id, messages.HELP),)
        if command == "/profile":
            return await self._profile(interaction.max_user_id)
        if command == "/checklist":
            return await self._checklist(interaction.max_user_id)
        if command == "/reset":
            await self._set_state(interaction.max_user_id, ConversationState.RESET_CONFIRM, {})
            return (_message(interaction.max_user_id, messages.RESET_PROMPT, keyboards.RESET),)
        return await self._state_text(interaction.max_user_id, text)

    async def handle_callback(
        self, interaction: CallbackInteraction
    ) -> tuple[OutgoingMessage, ...]:
        try:
            callback = parse_callback(interaction.payload)
        except InvalidCallback:
            return (_message(interaction.max_user_id, "Не понял эту кнопку. Попробуйте ещё раз."),)
        return await self._callback(interaction.max_user_id, callback)

    async def _start(self, max_user_id: int) -> tuple[OutgoingMessage, ...]:
        if await self._services.profiles.get_profile(max_user_id) is None:
            return (_message(max_user_id, messages.WELCOME, keyboards.WELCOME),)
        return (_message(max_user_id, messages.WELCOME_BACK, keyboards.WELCOME_BACK),)

    async def _profile(self, max_user_id: int) -> tuple[OutgoingMessage, ...]:
        profile = await self._services.profiles.get_profile(max_user_id)
        if profile is None:
            return (_message(max_user_id, messages.INN_PROMPT, keyboards.INN),)
        return (_message(max_user_id, render_profile(profile), keyboards.CONFIRM),)

    async def _state_text(self, max_user_id: int, text: str) -> tuple[OutgoingMessage, ...]:
        state, context = await self._state(max_user_id)
        if state is ConversationState.AWAITING_INN:
            return await self._lookup_inn(max_user_id, text)
        if state is ConversationState.MANUAL_REGION:
            await self._set_state(
                max_user_id,
                ConversationState.MANUAL_BUSINESS_FORM,
                context | {"region_code": text},
            )
            return (_message(max_user_id, messages.FORM_PROMPT, keyboards.BUSINESS_FORM),)
        return (_message(max_user_id, messages.UNSUPPORTED),)

    async def _lookup_inn(self, max_user_id: int, text: str) -> tuple[OutgoingMessage, ...]:
        try:
            profile = await self._services.onboarding.lookup_inn(max_user_id, text)
        except InvalidInn:
            return (_message(max_user_id, messages.INN_INVALID, keyboards.INN_ERROR),)
        except CompanyNotFound:
            return (_message(max_user_id, messages.INN_NOT_FOUND, keyboards.INN_ERROR),)
        except CompanyLookupUnavailable:
            return (_message(max_user_id, messages.INN_UNAVAILABLE, keyboards.INN_ERROR),)
        return (_message(max_user_id, render_profile(profile), keyboards.CONFIRM),)

    async def _callback(self, max_user_id: int, callback: Callback) -> tuple[OutgoingMessage, ...]:
        action = callback.action
        if action == "nav:start":
            await self._services.onboarding.start(max_user_id)
            return (_message(max_user_id, messages.INN_PROMPT, keyboards.INN),)
        if action == "nav:how":
            return (_message(max_user_id, messages.HOW_IT_WORKS),)
        if action in {"nav:help", "nav:profile", "nav:checklist"}:
            return await self.handle_text(TextInteraction(max_user_id, f"/{action.split(':')[1]}"))
        if action in {"inn:manual", "profile:edit", "profile:edit_manual"}:
            await self._services.onboarding.start_manual(max_user_id)
            return (_message(max_user_id, messages.REGION_PROMPT),)
        if action == "inn:retry":
            await self._services.onboarding.start(max_user_id)
            return (_message(max_user_id, messages.INN_PROMPT, keyboards.INN),)
        if action == "profile:confirm":
            await self._services.onboarding.confirm_profile(max_user_id)
            return await self._recommendations(max_user_id)
        if action == "reset:cancel":
            await self._set_state(max_user_id, ConversationState.READY, {})
            return (_message(max_user_id, "Оставил данные без изменений."),)
        if action == "reset:confirm":
            await self._services.profiles.delete_profile(max_user_id)
            await self._set_state(max_user_id, ConversationState.IDLE, {})
            return (_message(max_user_id, messages.RESET_DONE),)
        if action == "measure:details":
            return await self._details(max_user_id, callback)
        if action == "measure:add":
            return await self._add(max_user_id, callback)
        if action == "document:toggle":
            return await self._toggle(max_user_id, callback)
        if action == "investor:no" and self._services.investors is not None:
            await self._services.investors.decline(max_user_id)
            return (_message(max_user_id, "Хорошо, не буду больше спрашивать."),)
        return await self._manual_callback(max_user_id, callback)

    async def _manual_callback(
        self, max_user_id: int, callback: Callback
    ) -> tuple[OutgoingMessage, ...]:
        state, context = await self._state(max_user_id)
        if callback.action == "business_form" and state is ConversationState.MANUAL_BUSINESS_FORM:
            await self._set_state(
                max_user_id,
                ConversationState.MANUAL_SPHERE,
                context | {"business_form": callback.values[0]},
            )
            return (_message(max_user_id, messages.SPHERE_PROMPT, keyboards.SPHERE),)
        if callback.action == "sphere" and state is ConversationState.MANUAL_SPHERE:
            await self._set_state(
                max_user_id,
                ConversationState.MANUAL_STAGE,
                context | {"sphere": callback.values[0]},
            )
            return (_message(max_user_id, messages.STAGE_PROMPT, keyboards.STAGE),)
        if callback.action == "stage" and state is ConversationState.MANUAL_STAGE:
            await self._set_state(
                max_user_id,
                ConversationState.MANUAL_EMPLOYEES,
                context | {"business_stage": callback.values[0]},
            )
            return (_message(max_user_id, messages.EMPLOYEES_PROMPT, keyboards.EMPLOYEES),)
        if callback.action == "employees" and state is ConversationState.MANUAL_EMPLOYEES:
            data = context | {"employee_bucket": callback.values[0]}
            profile = await self._services.profiles.save_manual_profile(
                ProfileInput(
                    max_user_id=max_user_id,
                    region_code=str(data["region_code"]),
                    business_form=str(data["business_form"]),
                    sphere=str(data["sphere"]),
                    business_stage=str(data["business_stage"]),
                    employee_bucket=str(data["employee_bucket"]),
                )
            )
            await self._set_state(max_user_id, ConversationState.CONFIRM_PROFILE, {})
            return (_message(max_user_id, render_profile(profile), keyboards.CONFIRM),)
        return (_message(max_user_id, "Эта кнопка уже не актуальна. Используйте /start."),)

    async def _recommendations(self, max_user_id: int) -> tuple[OutgoingMessage, ...]:
        try:
            recommendations = await self._services.recommendations.recommend_for_user(max_user_id)
        except ProfileIncomplete:
            return (_message(max_user_id, messages.NEEDS_INFO),)
        if not recommendations:
            return (_message(max_user_id, messages.ZERO_RESULTS),)

        outgoing = [
            _message(
                max_user_id,
                render_measure(recommendation, recommendation.reasons),
                keyboards.measure(str(recommendation.measure_id)),
            )
            for recommendation in recommendations
            if recommendation.status is not MatchStatus.INELIGIBLE
        ]
        if self._services.investors is not None:
            if await self._services.investors.should_prompt(max_user_id):
                outgoing.append(_message(max_user_id, messages.INVESTOR_PROMPT, keyboards.INVESTOR))
        return tuple(outgoing) if outgoing else (_message(max_user_id, messages.ZERO_RESULTS),)

    async def _details(self, max_user_id: int, callback: Callback) -> tuple[OutgoingMessage, ...]:
        try:
            details = await self._services.recommendations.get_details(max_user_id, callback.uuid())
        except MeasureNotFound:
            return (_message(max_user_id, "Не нашёл эту меру. Подберите заново через /start."),)
        return (
            _message(
                max_user_id,
                render_measure_details(details, details.documents),
                keyboards.measure(str(details.measure_id)),
            ),
        )

    async def _add(self, max_user_id: int, callback: Callback) -> tuple[OutgoingMessage, ...]:
        try:
            checklist = await self._services.checklists.add_measure(max_user_id, callback.uuid())
        except MeasureNotFound:
            return (_message(max_user_id, "Не нашёл эту меру. Подберите заново через /start."),)
        return _render_checklist(max_user_id, checklist.checklists)

    async def _toggle(self, max_user_id: int, callback: Callback) -> tuple[OutgoingMessage, ...]:
        checklist = await self._services.checklists.toggle_document(max_user_id, callback.uuid())
        return _render_checklist(max_user_id, checklist.checklists)

    async def _checklist(self, max_user_id: int) -> tuple[OutgoingMessage, ...]:
        checklist = await self._services.checklists.list_checklists(max_user_id)
        return _render_checklist(max_user_id, checklist.checklists)

    async def _state(self, max_user_id: int) -> tuple[ConversationState, dict[str, object]]:
        return await self._services.states.get_state(max_user_id) or (ConversationState.IDLE, {})

    async def _set_state(
        self, max_user_id: int, state: ConversationState, context: dict[str, object]
    ) -> None:
        await self._services.states.set_state(max_user_id, state, context)


def _render_checklist(
    max_user_id: int, checklists: Sequence[object]
) -> tuple[OutgoingMessage, ...]:
    if not checklists:
        return (_message(max_user_id, messages.CHECKLIST_EMPTY),)
    outgoing: list[OutgoingMessage] = []
    for item in checklists:
        docs = getattr(item, "documents", ())
        lines = [
            f"{index}. {'готово' if getattr(doc, 'is_done', False) else 'не готово'}: {doc.title}"
            for index, doc in enumerate(docs, 1)
        ]
        text = f"{getattr(item, 'measure_name', 'Мера поддержки')}\n\n" + "\n".join(lines)
        outgoing.append(
            _message(
                max_user_id,
                text,
                *[keyboards.document(str(doc.id), doc.is_done) for doc in docs],
            )
        )
    return tuple(outgoing)


def _message(
    max_user_id: int, text: str, *keyboard_attachments: list[dict[str, object]]
) -> OutgoingMessage:
    return OutgoingMessage(
        max_user_id=max_user_id, text=text, buttons=_buttons(*keyboard_attachments)
    )


def _buttons(*keyboard_attachments: list[dict[str, object]]) -> tuple[tuple[Button, ...], ...]:
    rows: list[tuple[Button, ...]] = []
    for attachment in keyboard_attachments:
        for item in attachment:
            payload = item.get("payload", {})
            if not isinstance(payload, dict):
                continue
            buttons = payload.get("buttons", ())
            for row in buttons if isinstance(buttons, list) else ():
                rows.append(
                    tuple(
                        Button(str(button.get("text", "")), str(button.get("payload", "")))
                        for button in row
                        if isinstance(button, dict)
                    )
                )
    return tuple(row for row in rows if row)
