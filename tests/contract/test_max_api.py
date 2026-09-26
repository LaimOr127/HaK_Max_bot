import json

import httpx
import pytest

from navigator.infrastructure.max_api.client import MaxApiClient
from navigator.infrastructure.max_api.schemas import NewMessageBody


@pytest.mark.asyncio
async def test_me_uses_raw_authorization_header() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "secret-token"
        assert request.url.path == "/me"
        return httpx.Response(200, json={"user_id": 42, "username": "demo"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("secret-token", client=http)
        assert (await client.get_me())["user_id"] == 42


@pytest.mark.asyncio
async def test_updates_pass_marker_and_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["marker"] == "10"
        assert request.url.params["timeout"] == "30"
        assert request.extensions["timeout"]["read"] == 35
        return httpx.Response(200, json={"updates": [], "marker": 11})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("token", client=http, timeout_seconds=10)
        assert (await client.get_updates(marker=10, timeout_seconds=30))["marker"] == 11


@pytest.mark.asyncio
async def test_retry_after_429_is_bounded() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "slow down"})
        return httpx.Response(200, json={"user_id": 42})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("token", client=http, retries=1)
        assert (await client.get_me())["user_id"] == 42
    assert calls == 2


@pytest.mark.asyncio
async def test_callback_answer_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/answers"
        assert request.url.params["callback_id"] == "callback-1"
        assert b'"message"' in request.content
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("token", client=http)
        assert (await client.answer_callback("callback-1", message="Готово"))["success"] is True


@pytest.mark.asyncio
async def test_callback_answer_can_clear_inline_keyboard() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {"message": {"text": "✓ Выбрано", "attachments": []}}
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("token", client=http)
        await client.answer_callback(
            "callback-1", message=NewMessageBody(text="✓ Выбрано", attachments=[])
        )


@pytest.mark.asyncio
async def test_callback_answer_can_acknowledge_without_replacing_message() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {"notification": "Принято"}
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://platform-api2.max.ru"
    ) as http:
        client = MaxApiClient("token", client=http)
        await client.answer_callback("callback-1")
