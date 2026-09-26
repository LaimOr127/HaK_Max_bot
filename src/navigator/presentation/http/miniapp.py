from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from navigator.application.checklists import ChecklistService
from navigator.application.recommendations import RecommendationService
from navigator.domain.errors import ProfileIncomplete
from navigator.infrastructure.db.repositories import SqlAlchemyRepositories
from navigator.infrastructure.max_api.schemas import NewMessageBody
from navigator.presentation.maxbot.renderers import render_profile
from navigator.presentation.maxbot.runtime import SystemClock, _missing_profile_step

router = APIRouter()
_PAGE = Path.cwd() / "front" / "compare-card-screens.html"
_START = re.compile(r"^compare_([0-9a-fA-F-]{36})_([0-9a-fA-F-]{36})$")


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
    from navigator.bootstrap import settings

    if not settings.miniapp_enabled or settings.max_bot_token is None:
        raise HTTPException(503, "mini-app is not configured")
    user_id, _ = verify_user_data(x_max_init_data, settings.max_bot_token.get_secret_value())
    repos = SqlAlchemyRepositories(request.app.state.db_sessionmaker)
    async with repos.session() as bundle:
        profile = await bundle.profiles.get_by_user(user_id)
        complete = profile is not None and _missing_profile_step(profile) is None
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
            {"id": str(item.measure_id), "name": item.measure_name}
            for item in checklist.checklists
        ],
    }


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
    if (comparison_launch and requested != allowed_ids) or not set(requested).issubset(
        allowed_ids
    ):
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
