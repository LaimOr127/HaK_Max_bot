# mypy: disable-error-code = no-untyped-call
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from navigator.application.checklists import ChecklistService
from navigator.application.dto import FeedbackInput, InvestorLeadInput
from navigator.application.feedback import FeedbackService
from navigator.application.investors import InvestorService
from navigator.application.onboarding import OnboardingService
from navigator.application.profiles import ProfileService
from navigator.application.recommendations import RecommendationService
from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    ConversationState,
    EmployeeBucket,
    FeedbackType,
    ProfileSource,
    SphereCategory,
)
from navigator.domain.errors import CompanyLookupUnavailable, CompanyNotFound, InvalidInn
from navigator.infrastructure.db.repositories import SqlAlchemyRepositories
from navigator.infrastructure.fns.adapter import CompanyLookupAdapter
from navigator.infrastructure.max_api.client import MaxApiClient
from navigator.infrastructure.max_api.errors import MaxApiNetworkError, MaxApiServerError
from navigator.infrastructure.max_api.schemas import NewMessageBody
from navigator.ports.clock import Clock

from . import keyboards, messages
from .callbacks import InvalidCallback, parse_callback
from .renderers import render_measure, render_profile

log = logging.getLogger(__name__)


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()


@dataclass(frozen=True, slots=True)
class Incoming:
    user_id: int
    text: str | None = None
    callback_payload: str | None = None
    callback_id: str | None = None


class BotRuntime:
    def __init__(
        self,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        max_client: MaxApiClient,
        company_lookup: Any,
    ) -> None:
        self._repos = SqlAlchemyRepositories(sessionmaker)
        self._max = max_client
        self._lookup = CompanyLookupAdapter(company_lookup)
        self._clock = SystemClock()

    async def process_update(self, update: dict[str, Any]) -> None:
        incoming = _extract_incoming(update)
        if incoming is None:
            return
        try:
            if incoming.callback_payload is not None:
                await self._handle_callback(incoming)
            else:
                await self._handle_text(incoming)
        except Exception:
            log.exception("failed to process MAX update")
            await self._send(
                incoming.user_id, "Не получилось обработать действие. Попробуйте ещё раз."
            )

    async def _handle_text(self, incoming: Incoming) -> None:
        text = (incoming.text or "").strip()
        if text == "/help":
            await self._send(incoming.user_id, messages.HELP)
            return
        if text == "/start":
            await self._start(incoming.user_id)
            return
        if text == "/profile":
            await self._show_profile(incoming.user_id)
            return
        if text == "/checklist":
            await self._show_checklist(incoming.user_id)
            return
        if text == "/reset":
            async with self._repos.session() as repos:
                await repos.states.set_state(incoming.user_id, ConversationState.RESET_CONFIRM, {})
            await self._send(incoming.user_id, messages.RESET_PROMPT, keyboards.RESET)
            return

        async with self._repos.session() as repos:
            state = await repos.states.get_state(incoming.user_id)
            current = state[0] if state else ConversationState.IDLE
            context = state[1] if state else {}
            if current is ConversationState.AWAITING_INN:
                await self._lookup_inn(incoming.user_id, text)
            elif current is ConversationState.MANUAL_REGION:
                context["region_code"] = _region_code(text)
                await repos.states.set_state(
                    incoming.user_id, ConversationState.MANUAL_BUSINESS_FORM, context
                )
                await self._send(incoming.user_id, messages.FORM_PROMPT, keyboards.BUSINESS_FORM)
            elif current is ConversationState.FEEDBACK_TEXT:
                measure_id = UUID(str(context["measure_id"]))
                await FeedbackService(repos.feedback, repos.analytics).submit(
                    FeedbackInput(
                        incoming.user_id,
                        measure_id,
                        FeedbackType(str(context["feedback_type"])),
                        text,
                    )
                )
                await repos.states.set_state(incoming.user_id, ConversationState.READY, {})
                await self._send(incoming.user_id, "Спасибо, сохранили обратную связь.")
            elif current is ConversationState.INVESTOR_NAME:
                context["investor_name"] = text
                await repos.states.set_state(
                    incoming.user_id, ConversationState.INVESTOR_CONTACT, context
                )
                await self._send(
                    incoming.user_id, "Куда написать о запуске? Подойдёт телефон, email или @ник."
                )
            elif current is ConversationState.INVESTOR_CONTACT:
                await InvestorService(repos.investors, repos.analytics).submit_interest(
                    InvestorLeadInput(incoming.user_id, str(context.get("investor_name", "")), text)
                )
                await repos.states.set_state(incoming.user_id, ConversationState.READY, {})
                await self._send(incoming.user_id, "Готово, сообщим о запуске.")
            else:
                await self._send(incoming.user_id, messages.UNSUPPORTED)

    async def _handle_callback(self, incoming: Incoming) -> None:
        try:
            callback = parse_callback(incoming.callback_payload or "")
        except InvalidCallback:
            await self._send(incoming.user_id, "Кнопка устарела. Используйте /start.")
            return

        action = callback.action
        if action in {"nav:start", "inn:retry"}:
            async with self._repos.session() as repos:
                await OnboardingService(
                    repos.states, repos.profiles, self._lookup, repos.analytics
                ).start(incoming.user_id)
            await self._send(incoming.user_id, messages.INN_PROMPT, keyboards.INN)
            return
        if action == "nav:how":
            await self._send(incoming.user_id, messages.HOW_IT_WORKS)
            return
        if action == "nav:profile":
            await self._show_profile(incoming.user_id)
            return
        if action == "nav:checklist":
            await self._show_checklist(incoming.user_id)
            return
        if action == "inn:manual":
            async with self._repos.session() as repos:
                await OnboardingService(
                    repos.states, repos.profiles, self._lookup, repos.analytics
                ).start_manual(incoming.user_id)
            await self._send(incoming.user_id, messages.REGION_PROMPT)
            return
        if action == "profile:confirm":
            await self._after_profile_confirm(incoming.user_id)
            return
        if action == "reset:confirm":
            async with self._repos.session() as repos:
                await ProfileService(repos.profiles).delete_profile(incoming.user_id)
            await self._send(incoming.user_id, messages.RESET_DONE)
            return
        if action == "reset:cancel":
            async with self._repos.session() as repos:
                await repos.states.set_state(incoming.user_id, ConversationState.READY, {})
            await self._send(incoming.user_id, "Отменено.")
            return
        if action in {"business_form", "sphere", "stage", "employees"}:
            await self._handle_profile_answer(incoming.user_id, action, callback.values[0])
            return
        if action == "measure:details":
            await self._show_measure_details(incoming.user_id, callback.uuid())
            return
        if action == "measure:add":
            async with self._repos.session() as repos:
                await ChecklistService(
                    repos.checklists, repos.measures, repos.analytics
                ).add_measure(incoming.user_id, callback.uuid())
            await self._send(incoming.user_id, "Добавили в чек-лист. Откройте /checklist.")
            return
        if action == "document:toggle":
            async with self._repos.session() as repos:
                await ChecklistService(
                    repos.checklists, repos.measures, repos.analytics
                ).toggle_document(incoming.user_id, callback.uuid())
            await self._show_checklist(incoming.user_id)
            return
        if action == "measure:feedback":
            async with self._repos.session() as repos:
                await repos.states.set_state(
                    incoming.user_id,
                    ConversationState.FEEDBACK_REASON,
                    {"measure_id": str(callback.uuid())},
                )
            await self._send(
                incoming.user_id,
                "Что не так с мерой?",
                keyboards.inline_keyboard(
                    [
                        [("Не подхожу", f"feedback:not_eligible:{callback.values[0]}")],
                        [("Условия устарели", f"feedback:outdated:{callback.values[0]}")],
                        [("Другое", f"feedback:other:{callback.values[0]}")],
                    ]
                ),
            )
            return
        if action.startswith("feedback:"):
            feedback_type = action.split(":", 1)[1]
            async with self._repos.session() as repos:
                await repos.states.set_state(
                    incoming.user_id,
                    ConversationState.FEEDBACK_TEXT,
                    {"measure_id": callback.values[0], "feedback_type": feedback_type},
                )
            await self._send(incoming.user_id, "Напишите короткий комментарий.")
            return
        if action == "investor:yes":
            async with self._repos.session() as repos:
                await repos.states.set_state(incoming.user_id, ConversationState.INVESTOR_NAME, {})
            await self._send(incoming.user_id, "Как к вам обращаться?")
            return
        if action == "investor:no":
            async with self._repos.session() as repos:
                await InvestorService(repos.investors).decline(incoming.user_id)
            await self._send(incoming.user_id, "Хорошо.")
            return
        await self._send(incoming.user_id, "Действие пока недоступно.")

    async def _start(self, user_id: int) -> None:
        async with self._repos.session() as repos:
            profile = await ProfileService(repos.profiles).get_profile(user_id)
        if profile is None:
            await self._send(user_id, messages.WELCOME, keyboards.WELCOME)
        else:
            await self._send(user_id, messages.WELCOME_BACK, keyboards.WELCOME_BACK)

    async def _lookup_inn(self, user_id: int, text: str) -> None:
        async with self._repos.session() as repos:
            try:
                profile = await OnboardingService(
                    repos.states, repos.profiles, self._lookup, repos.analytics
                ).lookup_inn(user_id, text)
            except InvalidInn:
                await self._send(user_id, messages.INN_INVALID, keyboards.INN_ERROR)
                return
            except CompanyNotFound:
                await self._send(user_id, messages.INN_NOT_FOUND, keyboards.INN_ERROR)
                return
            except CompanyLookupUnavailable:
                await self._send(user_id, messages.INN_UNAVAILABLE, keyboards.INN_ERROR)
                return
        await self._send(user_id, render_profile(profile), keyboards.CONFIRM)

    async def _after_profile_confirm(self, user_id: int) -> None:
        async with self._repos.session() as repos:
            profile = await ProfileService(repos.profiles).get_profile(user_id)
            if profile is None:
                await repos.states.set_state(user_id, ConversationState.AWAITING_INN, {})
                await self._send(user_id, messages.INN_PROMPT, keyboards.INN)
                return
            step = _missing_profile_step(profile)
            if step is not None:
                await repos.states.set_state(user_id, step, _context_from_profile(profile))
                await self._send(user_id, _prompt_for_step(step), _keyboard_for_step(step))
                return
            await repos.states.set_state(user_id, ConversationState.READY, {})
        await self._show_recommendations(user_id)

    async def _handle_profile_answer(self, user_id: int, field: str, value: str) -> None:
        async with self._repos.session() as repos:
            state = await repos.states.get_state(user_id)
            context = state[1] if state else {}
            context[field] = value
            profile = await ProfileService(repos.profiles).get_profile(user_id)
            merged = _merge_profile(user_id, profile, context)
            await repos.profiles.save(merged)
            step = _missing_profile_step(merged)
            if step is not None:
                await repos.states.set_state(user_id, step, _context_from_profile(merged))
                await self._send(user_id, _prompt_for_step(step), _keyboard_for_step(step))
                return
            await repos.states.set_state(user_id, ConversationState.READY, {})
        await self._send(user_id, render_profile(merged), keyboards.CONFIRM)

    async def _show_profile(self, user_id: int) -> None:
        async with self._repos.session() as repos:
            profile = await ProfileService(repos.profiles).get_profile(user_id)
        if profile is None:
            await self._send(user_id, "Профиль ещё не заполнен. Начните с /start.")
        else:
            await self._send(user_id, render_profile(profile), keyboards.CONFIRM)

    async def _show_recommendations(self, user_id: int) -> None:
        async with self._repos.session() as repos:
            recommendations = await RecommendationService(
                repos.profiles, repos.measures, self._clock, repos.analytics
            ).recommend_for_user(user_id)
            if not recommendations:
                await self._send(user_id, messages.ZERO_RESULTS)
                return
            for item in recommendations:
                measure = await repos.measures.get(item.measure_id)
                if measure is not None:
                    await self._send(
                        user_id,
                        render_measure(measure, item.reasons),
                        keyboards.measure(str(measure.id)),
                    )
            if await InvestorService(repos.investors).should_prompt(user_id):
                await self._send(user_id, messages.INVESTOR_PROMPT, keyboards.INVESTOR)

    async def _show_measure_details(self, user_id: int, measure_id: UUID) -> None:
        async with self._repos.session() as repos:
            measure = await repos.measures.get(measure_id)
        if measure is None:
            await self._send(user_id, "Мера не найдена.")
            return
        docs = "\n".join(f"{i}. {doc.title}" for i, doc in enumerate(measure.documents, 1))
        await self._send(
            user_id,
            (
                f"{measure.name}\n\n{measure.what_is_it}\n\n"
                f"Кто может получить\n{measure.who_can_receive}\n\n"
                f"Документы\n{docs}\n\nКуда подавать\n{measure.where_to_apply}\n\n"
                f"Источник: {measure.source_name}\n{measure.source_url}"
            ),
            keyboards.measure(str(measure.id)),
        )

    async def _show_checklist(self, user_id: int) -> None:
        async with self._repos.session() as repos:
            dto = await ChecklistService(repos.checklists, repos.measures).list_checklists(user_id)
        if not dto.checklists:
            await self._send(user_id, messages.CHECKLIST_EMPTY)
            return
        for checklist in dto.checklists:
            lines = [f"Чек-лист: {checklist.measure_name}", ""]
            for doc in checklist.documents:
                mark = "✓" if doc.is_done else "□"
                lines.append(f"{mark} {doc.title}")
            await self._send(user_id, "\n".join(lines))
            for doc in checklist.documents:
                await self._send(user_id, doc.title, keyboards.document(str(doc.id), doc.is_done))

    async def _send(
        self, user_id: int, text: str, attachments: list[dict[str, object]] | None = None
    ) -> None:
        await self._max.send_message(
            NewMessageBody(text=text, attachments=attachments or []), user_id=user_id
        )

async def polling_loop(runtime: BotRuntime, max_client: MaxApiClient, timeout_seconds: int) -> None:
    marker: int | str | None = None
    while True:
        try:
            payload = await max_client.get_updates(marker=marker, timeout_seconds=timeout_seconds)
        except (MaxApiNetworkError, MaxApiServerError) as exc:
            log.warning("MAX polling retrying after temporary failure: %s", exc)
            await asyncio.sleep(5)
            continue
        marker = payload.get("marker", marker)
        for update in payload.get("updates", []):
            await runtime.process_update(update)
        await asyncio.sleep(0)


def _extract_incoming(update: dict[str, Any]) -> Incoming | None:
    nested_update = update.get("update")
    data: dict[str, Any] = nested_update if isinstance(nested_update, dict) else update
    update_type = data.get("update_type")
    if update_type == "bot_started":
        user = data.get("user")
        if isinstance(user, dict) and user.get("user_id") is not None:
            return Incoming(int(user["user_id"]), text="/start")
    nested_message = data.get("message")
    message: dict[str, Any] = nested_message if isinstance(nested_message, dict) else data
    user_raw = message.get("sender") or message.get("user") or data.get("user")
    user = user_raw if isinstance(user_raw, dict) else {}
    user_id = user.get("user_id") or user.get("id") or message.get("user_id") or data.get("user_id")
    callback_raw = data.get("callback")
    callback = callback_raw if isinstance(callback_raw, dict) else None
    if callback is not None:
        callback_user = callback.get("user")
        if isinstance(callback_user, dict):
            user = callback_user
        user_id = user.get("user_id") or user.get("id") or user_id
        payload = callback.get("payload") or callback.get("data")
        callback_id = callback.get("callback_id") or callback.get("id")
        if user_id is None or payload is None:
            return None
        return Incoming(
            int(user_id),
            callback_payload=str(payload),
            callback_id=str(callback_id) if callback_id is not None else None,
        )
    if user_id is None:
        return None
    body = message.get("body")
    text = body.get("text") if isinstance(body, dict) else None
    return Incoming(int(user_id), text=text or message.get("text") or data.get("text"))


def _missing_profile_step(profile: BusinessProfile) -> ConversationState | None:
    if profile.region_code is None:
        return ConversationState.MANUAL_REGION
    if profile.business_form is None:
        return ConversationState.MANUAL_BUSINESS_FORM
    if profile.sphere is None:
        return ConversationState.MANUAL_SPHERE
    if profile.business_stage is None:
        return ConversationState.MANUAL_STAGE
    if profile.employee_bucket is None and profile.employee_count is None:
        return ConversationState.MANUAL_EMPLOYEES
    return None


def _prompt_for_step(step: ConversationState) -> str:
    return {
        ConversationState.MANUAL_REGION: messages.REGION_PROMPT,
        ConversationState.MANUAL_BUSINESS_FORM: messages.FORM_PROMPT,
        ConversationState.MANUAL_SPHERE: messages.SPHERE_PROMPT,
        ConversationState.MANUAL_STAGE: messages.STAGE_PROMPT,
        ConversationState.MANUAL_EMPLOYEES: messages.EMPLOYEES_PROMPT,
    }[step]


def _keyboard_for_step(step: ConversationState) -> list[dict[str, object]] | None:
    return {
        ConversationState.MANUAL_REGION: None,
        ConversationState.MANUAL_BUSINESS_FORM: keyboards.BUSINESS_FORM,
        ConversationState.MANUAL_SPHERE: keyboards.SPHERE,
        ConversationState.MANUAL_STAGE: keyboards.STAGE,
        ConversationState.MANUAL_EMPLOYEES: keyboards.EMPLOYEES,
    }[step]


def _context_from_profile(profile: BusinessProfile) -> dict[str, object]:
    return {
        "region_code": profile.region_code,
        "business_form": _maybe_value(profile.business_form),
        "sphere": _maybe_value(profile.sphere),
        "stage": _maybe_value(profile.business_stage),
        "employees": _maybe_value(profile.employee_bucket),
    }


def _merge_profile(
    user_id: int, profile: BusinessProfile | None, context: dict[str, object]
) -> BusinessProfile:
    return BusinessProfile(
        max_user_id=user_id,
        region_code=str(context.get("region_code") or getattr(profile, "region_code", "") or "77"),
        sphere=_enum(SphereCategory, context.get("sphere"), getattr(profile, "sphere", None)),
        business_stage=_enum(
            BusinessStage, context.get("stage"), getattr(profile, "business_stage", None)
        ),
        business_form=_enum(
            BusinessForm, context.get("business_form"), getattr(profile, "business_form", None)
        ),
        employee_bucket=_enum(
            EmployeeBucket, context.get("employees"), getattr(profile, "employee_bucket", None)
        ),
        inn=getattr(profile, "inn", None),
        company_name=getattr(profile, "company_name", None),
        primary_okved=getattr(profile, "primary_okved", None),
        msp_category=getattr(profile, "msp_category", None),
        employee_count=getattr(profile, "employee_count", None),
        source=getattr(profile, "source", ProfileSource.MANUAL),
        consent_at=getattr(profile, "consent_at", None),
        fns_checked_at=getattr(profile, "fns_checked_at", None),
    )


def _enum(enum: Callable[[str], Any], value: object, fallback: Any) -> Any:
    return fallback if value in (None, "") else enum(str(value))


def _maybe_value(value: Any) -> str | None:
    return None if value is None else str(value)


def _region_code(text: str) -> str:
    raw = text.strip().lower()
    if raw.isdigit():
        return raw
    if "татар" in raw:
        return "16"
    if "москов" in raw and "обл" in raw:
        return "50"
    return "77" if "моск" in raw else raw[:16]
