from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from navigator.application.checklists import ChecklistService
from navigator.application.onboarding import OnboardingService, normalize_region
from navigator.application.recommendations import RecommendationService
from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    ConversationState,
    EmployeeBucket,
    SphereCategory,
)
from navigator.domain.errors import (
    CompanyLookupUnavailable,
    CompanyNotFound,
    InvalidInn,
    ProfileIncomplete,
)
from navigator.infrastructure.db.repositories import SqlAlchemyRepositories
from navigator.infrastructure.max_api.schemas import NewMessageBody
from navigator.presentation.maxbot.renderers import render_profile
from navigator.presentation.maxbot.runtime import SystemClock, _missing_profile_step

router = APIRouter()
_PAGE = Path.cwd() / "front" / "compare-card-screens.html"
_START = re.compile(r"^compare_([0-9a-fA-F-]{36})_([0-9a-fA-F-]{36})$")


class InnRequest(BaseModel):
    inn: str = Field(min_length=10, max_length=12)


class ManualProfileRequest(BaseModel):
    region_code: str = Field(min_length=2, max_length=50)
    business_form: BusinessForm
    sphere: SphereCategory
    business_stage: BusinessStage
    employee_bucket: EmployeeBucket


class ProfileSupplementRequest(BaseModel):
    region_code: str | None = Field(default=None, min_length=2, max_length=50)
    business_form: BusinessForm | None = None
    sphere: SphereCategory
    business_stage: BusinessStage
    employee_bucket: EmployeeBucket


def _profile_data(profile: BusinessProfile | None) -> dict[str, object] | None:
    if profile is None:
        return None
    return {
        "inn": profile.inn,
        "company_name": profile.company_name,
        "region_code": profile.region_code,
        "business_form": str(profile.business_form) if profile.business_form else None,
        "sphere": str(profile.sphere) if profile.sphere else None,
        "business_stage": str(profile.business_stage) if profile.business_stage else None,
        "employee_bucket": str(profile.employee_bucket) if profile.employee_bucket else None,
        "msp_category": str(profile.msp_category) if profile.msp_category else None,
        "primary_okved": profile.primary_okved,
        "source": str(profile.source),
    }


def _user_id(raw: str | None) -> int:
    from navigator.bootstrap import settings

    if not settings.miniapp_enabled or settings.max_bot_token is None:
        raise HTTPException(503, "mini-app is not configured")
    return verify_user_data(raw, settings.max_bot_token.get_secret_value())[0]


@router.get("/miniapp", response_class=HTMLResponse)
@router.get("/miniapp/compare", response_class=HTMLResponse)
async def compare_page() -> HTMLResponse:
    return HTMLResponse(_PAGE.read_text(encoding="utf-8"))


def verify_user_data(
    raw: str | None, token: str, *, now: int | None = None
) -> tuple[int, dict[str, str]]:
    """Verify signed MAX Bridge data before trusting the user."""
    if not raw or len(raw) > 8192:
        raise HTTPException(401, "invalid MAX init data")
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        data = dict(pairs)
        original_hash = data.pop("hash")
        if len(data) + 1 != len(pairs) or not re.fullmatch(r"[0-9a-fA-F]{64}", original_hash):
            raise ValueError("duplicate field or bad hash")
        check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, original_hash.lower()):
            raise ValueError("signature mismatch")
        age = (now if now is not None else int(time.time())) - int(data["auth_date"])
        if age < -60 or age > 3600:
            raise ValueError("expired init data")
        user = json.loads(data["user"])
        user_id = user["id"]
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("invalid user")
        return user_id, data
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(401, "invalid MAX init data") from exc


def verify_init_data(
    raw: str | None, token: str, *, now: int | None = None
) -> tuple[int, tuple[UUID, UUID]]:
    """Verify a comparison launch payload as well as the MAX user."""
    user_id, data = verify_user_data(raw, token, now=now)
    match = _START.fullmatch(data.get("start_param", ""))
    if match is None:
        raise HTTPException(401, "invalid MAX init data")
    ids = (UUID(match[1]), UUID(match[2]))
    if ids[0] == ids[1]:
        raise HTTPException(401, "invalid MAX init data")
    return user_id, ids


@router.get("/api/miniapp/home")
async def home_data(
    request: Request, x_max_init_data: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = _user_id(x_max_init_data)
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        profile = await bundle.profiles.get_by_user(user_id)
        state = await bundle.states.get_state(user_id)
        complete = (
            profile is not None
            and _missing_profile_step(profile) is None
            and state is not None
            and state[0] is ConversationState.READY
        )
        recommendations = (
            await RecommendationService(
                bundle.profiles, bundle.measures, SystemClock()
            ).recommend_for_user(user_id, limit=5)
            if complete
            else ()
        )
        checklist = await ChecklistService(bundle.checklists, bundle.measures).list_checklists(
            user_id
        )
    return {
        "profile": _profile_data(profile),
        "profile_text": render_profile(profile).split("\n\nВсё верно")[0] if profile else None,
        "profile_complete": complete,
        "recommendations": [
            {
                "id": str(item.measure_id),
                "name": item.name,
                "amount_display": item.amount_display,
                "support_level": item.support_level,
                "status": item.status.value,
                "reasons": list(item.reasons),
            }
            for item in recommendations
        ],
        "checklist": [
            {"id": str(item.measure_id), "name": item.measure_name} for item in checklist.checklists
        ],
    }


@router.post("/api/miniapp/lookup")
async def lookup_company(
    request: Request, body: InnRequest, x_max_init_data: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = _user_id(x_max_init_data)
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    try:
        async with repos.session() as bundle:
            profile = await OnboardingService(
                bundle.states, bundle.profiles, request.app.state.company_lookup, bundle.analytics
            ).lookup_inn(user_id, body.inn)
    except InvalidInn as exc:
        raise HTTPException(400, "Проверьте ИНН: неверная длина или контрольная цифра.") from exc
    except CompanyNotFound as exc:
        raise HTTPException(404, "Компания с таким ИНН не найдена.") from exc
    except CompanyLookupUnavailable as exc:
        raise HTTPException(
            503, "Реестр ФНС временно недоступен. Повторите позже или заполните вручную."
        ) from exc
    return {"profile": _profile_data(profile)}


@router.post("/api/miniapp/manual")
async def save_manual_profile(
    request: Request,
    body: ManualProfileRequest,
    x_max_init_data: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _user_id(x_max_init_data)
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        service = OnboardingService(
            bundle.states, bundle.profiles, request.app.state.company_lookup, bundle.analytics
        )
        await service.start_manual(user_id)
        await service.set_manual_region(user_id, body.region_code)
        await service.set_manual_form(user_id, body.business_form.value)
        await service.set_manual_sphere(user_id, body.sphere.value)
        await service.set_manual_stage(user_id, body.business_stage.value)
        profile = await service.finish_manual(user_id, body.employee_bucket.value)
    return {"profile": _profile_data(profile)}


@router.post("/api/miniapp/profile")
async def supplement_profile(
    request: Request,
    body: ProfileSupplementRequest,
    x_max_init_data: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _user_id(x_max_init_data)
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        current = await bundle.profiles.get_by_user(user_id)
        if current is None:
            raise HTTPException(
                404, "Сначала найдите компанию по ИНН или заполните профиль вручную."
            )
        profile = replace(
            current,
            region_code=(
                normalize_region(body.region_code) if body.region_code else current.region_code
            ),
            business_form=body.business_form or current.business_form,
            sphere=body.sphere,
            business_stage=body.business_stage,
            employee_bucket=body.employee_bucket,
        )
        await bundle.profiles.save(profile)
        await bundle.states.set_state(user_id, ConversationState.CONFIRM_PROFILE, {})
    return {"profile": _profile_data(profile)}


@router.post("/api/miniapp/confirm")
async def confirm_profile(
    request: Request, x_max_init_data: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = _user_id(x_max_init_data)
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        profile = await bundle.profiles.get_by_user(user_id)
        if profile is None:
            raise HTTPException(404, "Профиль не найден.")
        if _missing_profile_step(profile) is not None:
            raise HTTPException(409, "Уточните недостающие данные профиля.")
        await OnboardingService(
            bundle.states, bundle.profiles, request.app.state.company_lookup, bundle.analytics
        ).confirm_profile(user_id)
    return {"profile": _profile_data(profile)}


async def _authorized(request: Request, raw: str | None) -> tuple[int, tuple[UUID, ...], bool]:
    from navigator.bootstrap import settings

    if not settings.miniapp_enabled or settings.max_bot_token is None:
        raise HTTPException(503, "mini-app is not configured")
    token = settings.max_bot_token.get_secret_value()
    user_id, data = verify_user_data(raw, token)
    comparison_launch = data.get("start_param", "").startswith("compare_")
    signed_ids = verify_init_data(raw, token)[1] if comparison_launch else None
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        state = await bundle.states.get_state(user_id)
        if state is None or state[0] is not ConversationState.READY:
            raise HTTPException(403, "profile is not confirmed")
        try:
            suggestions = await RecommendationService(
                bundle.profiles, bundle.measures, SystemClock()
            ).recommend_for_user(user_id, limit=5)
        except ProfileIncomplete as exc:
            raise HTTPException(403, "profile is incomplete") from exc
        recommended_ids = tuple(item.measure_id for item in suggestions)
        if signed_ids is not None and not set(signed_ids).issubset(recommended_ids):
            raise HTTPException(403, "measures are not recommended for this profile")
    return user_id, signed_ids or recommended_ids, comparison_launch


@router.get("/api/miniapp/compare")
async def compare_data(
    request: Request,
    ids: str = Query(),
    x_max_init_data: str | None = Header(default=None),
) -> dict[str, object]:
    user_id, allowed_ids, comparison_launch = await _authorized(request, x_max_init_data)
    try:
        requested = tuple(UUID(part) for part in ids.split(","))
    except ValueError as exc:
        raise HTTPException(400, "invalid measure ids") from exc
    if len(requested) != 2 or requested[0] == requested[1]:
        raise HTTPException(400, "two distinct measures are required")
    if (comparison_launch and requested != allowed_ids) or not set(requested).issubset(allowed_ids):
        raise HTTPException(403, "measures are not available for this launch")
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        checklist = await ChecklistService(bundle.checklists, bundle.measures).list_checklists(
            user_id
        )
        checked = {entry.measure_id for entry in checklist.checklists}
        result = []
        for measure_id in requested:
            measure = await bundle.measures.get(measure_id)
            if measure is None:
                raise HTTPException(404, "measure not found")
            result.append(
                {
                    "id": str(measure.id),
                    "name": measure.name,
                    "support_level": measure.support_level.value,
                    "amount_display": measure.amount_display,
                    "review_days": measure.review_days,
                    "documents": [document.title for document in measure.documents],
                    "who_can_receive": measure.who_can_receive,
                    "what_is_it": measure.what_is_it,
                    "checklisted": measure_id in checked,
                }
            )
    return {"measures": result}


@router.get("/api/miniapp/measures/{measure_id}")
async def measure_detail(
    measure_id: UUID,
    request: Request,
    x_max_init_data: str | None = Header(default=None),
) -> dict[str, object]:
    user_id, allowed_ids, _ = await _authorized(request, x_max_init_data)
    if measure_id not in allowed_ids:
        raise HTTPException(403, "measure is not recommended for this profile")
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        measure = await bundle.measures.get(measure_id)
        if measure is None:
            raise HTTPException(404, "measure not found")
        checklist = await ChecklistService(bundle.checklists, bundle.measures).list_checklists(
            user_id
        )
    return {
        "id": str(measure.id),
        "name": measure.name,
        "support_level": measure.support_level.value,
        "amount_display": measure.amount_display,
        "what_is_it": measure.what_is_it,
        "who_can_receive": measure.who_can_receive,
        "where_to_apply": measure.where_to_apply,
        "documents": [item.title for item in measure.documents],
        "source_name": measure.source_name,
        "source_url": measure.source_url,
        "source_checked_at": measure.source_checked_at.isoformat(),
        "review_days": measure.review_days,
        "checklisted": any(item.measure_id == measure_id for item in checklist.checklists),
    }


@router.post("/api/miniapp/checklist/{measure_id}")
@router.delete("/api/miniapp/checklist/{measure_id}")
async def change_checklist(
    measure_id: UUID,
    request: Request,
    x_max_init_data: str | None = Header(default=None),
) -> dict[str, bool]:
    user_id, ids, _ = await _authorized(request, x_max_init_data)
    if measure_id not in ids:
        raise HTTPException(403, "measure is not in this comparison")
    adding = request.method == "POST"
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        service = ChecklistService(bundle.checklists, bundle.measures, bundle.analytics)
        if adding:
            await service.add_measure(user_id, measure_id)
        else:
            await service.remove_measure(user_id, measure_id)
        measure = await bundle.measures.get(measure_id)
    client = request.app.state.max_client
    if client is not None and measure is not None:
        try:
            action = "добавлена в чек-лист" if adding else "удалена из чек-листа"
            await client.send_message(
                NewMessageBody(text=f"«{measure.name}» {action}."), user_id=user_id
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("could not send mini-app checklist confirmation")
    return {"checklisted": adding}
