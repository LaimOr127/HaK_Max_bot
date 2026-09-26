import hashlib
import hmac
import json
import time
from datetime import date
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from navigator import bootstrap
from navigator.bootstrap import app
from navigator.domain.entities import Measure, MeasureDocument
from navigator.domain.enums import SupportLevel
from navigator.presentation.http import miniapp
from navigator.presentation.http.miniapp import verify_init_data, verify_user_data
from navigator.presentation.maxbot.keyboards import compare, home

FIRST = UUID("11111111-1111-4111-8111-111111111111")
SECOND = UUID("22222222-2222-4222-8222-222222222222")


def signed_data(*, user_id: int = 42, auth_date: int = 1000, start: str | None = None) -> str:
    data = {
        "auth_date": str(auth_date),
        "start_param": start or f"compare_{FIRST}_{SECOND}",
        "user": json.dumps({"id": user_id}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", b"token", hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def test_max_signature_binds_user_and_two_measures() -> None:
    assert verify_init_data(signed_data(), "token", now=1000) == (42, (FIRST, SECOND))
    button = compare("demo_bot", str(FIRST), str(SECOND))[0]["payload"]["buttons"][0][0]
    assert button == {
        "type": "open_app",
        "text": "Сравнить",
        "web_app": "demo_bot",
        "payload": f"compare_{FIRST}_{SECOND}",
    }


def test_home_launch_verifies_user_without_comparison_payload() -> None:
    user_id, data = verify_user_data(signed_data(start="home"), "token", now=1000)
    assert user_id == 42
    assert data["start_param"] == "home"
    assert home("demo_bot")[0]["payload"]["buttons"][0][0] == {
        "type": "open_app",
        "text": "Открыть навигатор",
        "web_app": "demo_bot",
        "payload": "home",
    }
    with pytest.raises(HTTPException):
        verify_user_data(
            signed_data(start="home").replace("id%22%3A42", "id%22%3A43"),
            "token",
            now=1000,
        )


@pytest.mark.parametrize(
    "raw, now",
    [
        (signed_data().replace("id%22%3A42", "id%22%3A43"), 1000),
        (signed_data(auth_date=1), 5000),
        (signed_data(start=f"compare_{FIRST}_{FIRST}"), 1000),
        (signed_data() + "&hash=bad", 1000),
        ("", 1000),
    ],
)
def test_max_signature_rejects_tampering_expiry_and_invalid_payload(raw: str, now: int) -> None:
    with pytest.raises(HTTPException) as exc:
        verify_init_data(raw, "token", now=now)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_miniapp_page_is_served_without_mock_data() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/miniapp/compare")
        home_response = await client.get("/miniapp")
    assert response.status_code == 200
    assert home_response.status_code == 200
    assert "/api/miniapp/home" in home_response.text
    assert '<script src="https://st.max.ru/js/max-web-app.js" async></script>' in response.text
    assert "/api/miniapp/compare" in response.text
    assert "window.Max && window.Max.WebApp" in response.text
    assert 'queryValue("WebAppData")' in response.text
    assert 'queryValue("init_data")' in response.text
    assert 'new URLSearchParams(initData).get("start_param")' in response.text
    assert 'data-home-compare' in response.text
    assert "Субсидия на оборудование" not in response.text


@pytest.mark.asyncio
async def test_home_api_uses_signed_user_profile(monkeypatch) -> None:
    profile = SimpleNamespace(
        region_code="77", business_form="ooo", sphere="it_digital",
        business_stage="gt3", employee_bucket="16_100", inn="9715384111",
        company_name="Компания", primary_okved="62.01", msp_category=None,
        source="fns",
    )

    class Profiles:
        async def get_by_user(self, user_id):
            assert user_id == 42
            return profile

    class Measures:
        async def list_active_candidates(self, today):
            return []

    class Checklists:
        async def list_by_user(self, user_id):
            assert user_id == 42
            return []

    class RepoSession:
        async def __aenter__(self):
            return SimpleNamespace(
                profiles=Profiles(), measures=Measures(), checklists=Checklists()
            )

        async def __aexit__(self, *args):
            return None

    class Repos:
        def __init__(self, sessionmaker):
            pass

        def session(self):
            return RepoSession()

    monkeypatch.setattr(miniapp, "SqlAlchemyRepositories", Repos)
    monkeypatch.setattr(
        bootstrap,
        "settings",
        SimpleNamespace(miniapp_enabled=True, max_bot_token=SecretStr("token")),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_sessionmaker=None)))
    result = await miniapp.home_data(
        request, x_max_init_data=signed_data(start="home", auth_date=int(time.time()))
    )
    assert result["profile_complete"] is True
    assert "Компания" in result["profile_text"]
    assert result["recommendations"] == []


@pytest.mark.asyncio
async def test_home_launch_can_compare_only_recommended_measures(monkeypatch) -> None:
    class RepoSession:
        async def __aenter__(self):
            return SimpleNamespace(profiles=None, measures=None)

        async def __aexit__(self, *args):
            return None

    class Repos:
        def __init__(self, sessionmaker):
            pass

        def session(self):
            return RepoSession()

    class Recommendations:
        def __init__(self, *args):
            pass

        async def recommend_for_user(self, user_id, limit):
            assert user_id == 42 and limit == 5
            return [SimpleNamespace(measure_id=FIRST), SimpleNamespace(measure_id=SECOND)]

    monkeypatch.setattr(miniapp, "SqlAlchemyRepositories", Repos)
    monkeypatch.setattr(miniapp, "RecommendationService", Recommendations)
    monkeypatch.setattr(
        bootstrap,
        "settings",
        SimpleNamespace(miniapp_enabled=True, max_bot_token=SecretStr("token")),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_sessionmaker=None)))
    now = int(time.time())
    assert await miniapp._authorized(request, signed_data(start="home", auth_date=now)) == (
        42, (FIRST, SECOND), False
    )
    assert await miniapp._authorized(request, signed_data(auth_date=now)) == (
        42, (FIRST, SECOND), True
    )


@pytest.mark.asyncio
async def test_compare_api_returns_only_signed_measures_and_shared_checklist(monkeypatch) -> None:
    measures = {
        measure_id: Measure(
            id=measure_id,
            external_code=str(measure_id),
            name=f"Мера {number}",
            support_level=SupportLevel.FEDERAL,
            amount_display="До 100 000 ₽",
            what_is_it="Описание",
            who_can_receive="Малый бизнес",
            where_to_apply="Портал",
            source_name="Источник",
            source_url="https://example.org",
            source_checked_at=date(2026, 9, 25),
            documents=(MeasureDocument(FIRST, measure_id, "form", "Заявление"),),
        )
        for number, measure_id in enumerate((FIRST, SECOND), 1)
    }

    class MeasureRepo:
        async def get(self, measure_id):
            return measures.get(measure_id)

    class ChecklistRepo:
        async def list_by_user(self, user_id):
            assert user_id == 42
            return [SimpleNamespace(measure_id=FIRST)]

    class RepoSession:
        async def __aenter__(self):
            return SimpleNamespace(measures=MeasureRepo(), checklists=ChecklistRepo())

        async def __aexit__(self, *args):
            return None

    class Repos:
        def __init__(self, sessionmaker):
            pass

        def session(self):
            return RepoSession()

    async def authorized(request, raw):
        return 42, (FIRST, SECOND), True

    monkeypatch.setattr(miniapp, "_authorized", authorized)
    monkeypatch.setattr(miniapp, "SqlAlchemyRepositories", Repos)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_sessionmaker=None)))
    response = await miniapp.compare_data(request, f"{FIRST},{SECOND}")
    assert [item["name"] for item in response["measures"]] == ["Мера 1", "Мера 2"]
    assert [item["checklisted"] for item in response["measures"]] == [True, False]
    with pytest.raises(HTTPException) as exc:
        await miniapp.compare_data(request, f"{SECOND},{FIRST}")
    assert exc.value.status_code == 403
    async def authorized_home(request, raw):
        return 42, (FIRST, SECOND), False

    monkeypatch.setattr(miniapp, "_authorized", authorized_home)
    home_response = await miniapp.compare_data(request, f"{SECOND},{FIRST}")
    assert [item["id"] for item in home_response["measures"]] == [str(SECOND), str(FIRST)]
    with pytest.raises(HTTPException) as exc:
        await miniapp.compare_data(request, f"{FIRST},33333333-3333-4333-8333-333333333333")
    assert exc.value.status_code == 403
