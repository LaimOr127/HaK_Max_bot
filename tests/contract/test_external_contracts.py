import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from navigator.config import Settings
from navigator.infrastructure.fns.local_snapshot import LocalSnapshotCompanyLookup
from navigator.infrastructure.fns.rmsp_portal import RmspPortalCompanyLookup
from navigator.infrastructure.max_api.errors import MaxApiNetworkError
from navigator.infrastructure.openrouter.client import OpenRouterClient
from navigator.infrastructure.redis.cache import RedisJsonCache
from navigator.infrastructure.redis.idempotency import RedisIdempotencyStore
from navigator.infrastructure.redis.rate_limit import RedisRateLimiter
from navigator.presentation.maxbot.runtime import polling_loop


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.calls = []
        self.fail = False

    async def set(self, key, value, ex=None, nx=False):
        self.calls.append(("set", key, value, ex, nx))
        if self.fail:
            raise RuntimeError("redis down")
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        self.calls.append(("get", key))
        if self.fail:
            raise RuntimeError("redis down")
        return self.values.get(key)

    async def delete(self, key):
        self.calls.append(("delete", key))
        if self.fail:
            raise RuntimeError("redis down")
        return int(key in self.values and self.values.pop(key) is not None)

    async def incr(self, key):
        self.calls.append(("incr", key))
        if self.fail:
            raise RuntimeError("redis down")
        self.values[key] = str(int(self.values.get(key, "0")) + 1)
        return int(self.values[key])

    async def expire(self, key, seconds):
        self.calls.append(("expire", key, seconds))
        if self.fail:
            raise RuntimeError("redis down")
        return True


@pytest.mark.asyncio
async def test_rmsp_lookup_posts_form_query_and_maps_matching_company() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.content == b"mode=quick&query=7712345678"
        return httpx.Response(
            200,
            json={"data": [{"inn": "7712345678", "name": "Demo LLC", "region": "77"}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await RmspPortalCompanyLookup(client=http).lookup_by_inn("77 12345678")

    assert result.status == "found"
    assert result.company is not None
    assert result.company.name == "Demo LLC"


@pytest.mark.asyncio
async def test_rmsp_lookup_treats_unusable_rows_as_schema_drift() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"inn": "7712345678"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await RmspPortalCompanyLookup(client=http).lookup_by_inn("7712345678")

    assert result.status == "unavailable"
    assert result.reason == "schema_drift"


@pytest.mark.asyncio
async def test_rmsp_lookup_maps_the_current_official_search_shape() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "inn": "9715384111",
                        "name_ex": "ООО ИАС ДИДЖИТАЛ",
                        "ogrn": "1207700181171",
                        "okved1": "62.01",
                        "regioncode": "77",
                        "category": 1,
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await RmspPortalCompanyLookup(client=http).lookup_by_inn("9715384111")

    assert result.status == "found"
    assert result.company is not None
    assert result.company.name == "ООО ИАС ДИДЖИТАЛ"
    assert result.company.okved == "62.01"
    assert result.company.region == "77"
    assert result.company.sme_category == "micro"


@pytest.mark.asyncio
async def test_rmsp_lookup_falls_back_to_transparent_business_for_non_sme_company() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "rmsp.nalog.ru":
            return httpx.Response(200, json={"data": []})
        if len(requests) == 2:
            assert request.content == b"mode=search-all&queryAll=7707083893&page=1&pageSize=10"
            return httpx.Response(200, json={"id": "request-1"})
        assert request.content == b"id=request-1&method=get-response"
        return httpx.Response(
            200,
            json={
                "ul": {
                    "data": [
                        {
                            "inn": "7707083893",
                            "namep": "ПАО СБЕРБАНК",
                            "ogrn": "1027700132195",
                            "okved2main": "64.19",
                        }
                    ]
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await RmspPortalCompanyLookup(client=http, poll_delays=(0,)).lookup_by_inn(
            "7707083893"
        )

    assert result.status == "found"
    assert result.source == "transparent_business"
    assert result.company is not None
    assert result.company.name == "ПАО СБЕРБАНК"
    assert result.company.region == "77"


@pytest.mark.asyncio
async def test_rmsp_lookup_uses_transparent_business_when_smeregister_is_unavailable() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.host == "rmsp.nalog.ru":
            return httpx.Response(503)
        if calls == 2:
            return httpx.Response(200, json={"id": "request-1"})
        return httpx.Response(
            200,
            json={"ul": {"data": [{"inn": "7707083893", "namep": "ПАО СБЕРБАНК"}]}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await RmspPortalCompanyLookup(client=http, poll_delays=(0,)).lookup_by_inn(
            "7707083893"
        )

    assert result.status == "found"
    assert result.source == "transparent_business"


@pytest.mark.asyncio
async def test_openrouter_chat_sends_privacy_preserving_non_stream_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/chat/completions"
        assert payload["model"] == "demo-model"
        assert payload["stream"] is False
        assert payload["provider"] == {"zdr": True, "data_collection": "deny"}
        return httpx.Response(200, json={"choices": [{"message": {"content": "  ok  "}}]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://openrouter.test"
    ) as http:
        result = await OpenRouterClient("key", "demo-model", client=http).chat(
            [{"role": "user", "content": "hi"}]
        )

    assert result == "ok"


@pytest.mark.asyncio
async def test_redis_idempotency_uses_nx_ttl_and_rejects_duplicate() -> None:
    redis = FakeRedis()
    store = RedisIdempotencyStore(redis, prefix="webhook")

    assert await store.mark_once("event-1", 30) is True
    assert await store.mark_once("event-1", 30) is False
    assert redis.calls[0] == ("set", "webhook:event-1", "1", 30, True)


@pytest.mark.asyncio
async def test_redis_idempotency_fails_closed_when_redis_is_down() -> None:
    redis = FakeRedis()
    redis.fail = True

    with pytest.raises(RuntimeError, match="redis down"):
        await RedisIdempotencyStore(redis).mark_once("event-1", 30)


@pytest.mark.asyncio
async def test_redis_helpers_fail_open_or_soft_when_redis_is_down() -> None:
    redis = FakeRedis()
    redis.fail = True

    assert await RedisRateLimiter(redis).allow("user-1", limit=1, window_seconds=60) is True
    assert await RedisJsonCache(redis).get("user-1") is None
    assert await RedisJsonCache(redis).set("user-1", {"ok": True}, 60) is False
    assert await RedisJsonCache(redis).delete("user-1") is False


def test_webhook_transport_requires_public_url_secret_and_bot_token() -> None:
    with pytest.raises(ValidationError):
        Settings(max_transport="webhook")


def test_webhook_transport_accepts_complete_secret_settings() -> None:
    settings = Settings(
        max_transport="webhook",
        max_webhook_public_url="https://bot.example.com/webhook",
        max_webhook_secret="secret",  # noqa: S106
        max_bot_token="token",  # noqa: S106
    )

    assert settings.max_webhook_secret is not None
    assert settings.max_bot_token is not None


def test_settings_reads_reminder_days_from_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("REMINDER_DAYS=[7,3,1]\n", encoding="utf-8")

    assert Settings(_env_file=env_file).reminder_days == (7, 3, 1)


def test_settings_ignores_empty_optional_values_from_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MAX_WEBHOOK_PUBLIC_URL=\n", encoding="utf-8")

    assert Settings(_env_file=env_file).max_webhook_public_url is None


@pytest.mark.asyncio
async def test_polling_retries_after_network_error(monkeypatch) -> None:
    class Client:
        calls = 0

        async def get_updates(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise MaxApiNetworkError("network unavailable")
            raise asyncio.CancelledError

    delays: list[int] = []

    async def sleep(seconds: int) -> None:
        delays.append(seconds)

    monkeypatch.setattr("navigator.presentation.maxbot.runtime.asyncio.sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        await polling_loop(None, Client(), 30)

    assert delays == [5]


@pytest.mark.asyncio
async def test_local_snapshot_skips_rows_without_valid_inn_or_name(tmp_path) -> None:
    snapshot = tmp_path / "companies.csv"
    snapshot.write_text(
        "inn,name,region\n7712345678,Demo LLC,77\nbad,Broken,77\n1234567890,,50\n",
        encoding="utf-8",
    )

    found = await LocalSnapshotCompanyLookup(snapshot).lookup_by_inn("7712345678")
    missing = await LocalSnapshotCompanyLookup(snapshot).lookup_by_inn("1234567890")

    assert found.status == "found"
    assert missing.status == "not_found"
