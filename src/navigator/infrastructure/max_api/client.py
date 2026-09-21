from __future__ import annotations

import asyncio
import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .errors import (
    MaxApiAuthError,
    MaxApiClientError,
    MaxApiError,
    MaxApiNetworkError,
    MaxApiServerError,
)
from .schemas import BotCommand, JsonDict, NewMessageBody

MAX_API_BASE_URL = "https://platform-api2.max.ru"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class MaxApiClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = MAX_API_BASE_URL,
        timeout_seconds: float = 10.0,
        retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not token:
            raise ValueError("MAX token is required")
        self._own_client = client is None
        self._retries = retries
        self._token = token
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Authorization": token},
        )

    async def __aenter__(self) -> MaxApiClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def get_me(self) -> JsonDict:
        return await self._request("GET", "/me")

    async def get_updates(
        self,
        *,
        marker: int | str | None = None,
        limit: int | None = None,
        timeout_seconds: int | None = None,
    ) -> JsonDict:
        params: JsonDict = {}
        if marker is not None:
            params["marker"] = marker
        if limit is not None:
            params["limit"] = limit
        if timeout_seconds is not None:
            params["timeout"] = timeout_seconds
        return await self._request("GET", "/updates", params=params)

    async def send_message(
        self,
        body: NewMessageBody | JsonDict | str,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        disable_link_preview: bool | None = None,
    ) -> JsonDict:
        if (user_id is None) == (chat_id is None):
            raise ValueError("Exactly one of user_id or chat_id is required")
        params: JsonDict = {"user_id": user_id} if user_id is not None else {"chat_id": chat_id}
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview
        return await self._request(
            "POST",
            "/messages",
            params=params,
            json=self._message_payload(body),
        )

    async def edit_message(
        self,
        message_id: str,
        body: NewMessageBody | JsonDict | str,
        *,
        disable_link_preview: bool | None = None,
    ) -> JsonDict:
        params: JsonDict = {"message_id": message_id}
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview
        return await self._request(
            "PUT",
            "/messages",
            params=params,
            json=self._message_payload(body),
        )

    async def answer_callback(
        self,
        callback_id: str,
        *,
        message: NewMessageBody | JsonDict | str | None = None,
        disable_link_preview: bool | None = None,
    ) -> JsonDict:
        params: JsonDict = {"callback_id": callback_id}
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview
        payload: JsonDict = {}
        if message is not None:
            payload["message"] = self._message_payload(message)
        return await self._request("POST", "/answers", params=params, json=payload)

    async def create_subscription(
        self,
        url: str,
        *,
        update_types: list[str] | None = None,
        secret: str | None = None,
    ) -> JsonDict:
        payload: JsonDict = {"url": url}
        if update_types:
            payload["update_types"] = update_types
        if secret:
            payload["secret"] = secret
        return await self._request("POST", "/subscriptions", json=payload)

    async def list_subscriptions(self) -> JsonDict:
        return await self._request("GET", "/subscriptions")

    async def delete_subscription(self, url: str) -> JsonDict:
        return await self._request("DELETE", "/subscriptions", params={"url": url})

    async def set_commands(self, commands: list[BotCommand | JsonDict]) -> JsonDict:
        payload = {
            "commands": [
                command.to_payload() if isinstance(command, BotCommand) else command
                for command in commands
            ]
        }
        return await self._request("PATCH", "/me/commands", json=payload)

    async def _request(self, method: str, path: str, **kwargs: Any) -> JsonDict:
        last_error: MaxApiError | None = None
        headers = {"Authorization": self._token, **kwargs.pop("headers", {})}
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(method, path, headers=headers, **kwargs)
            except httpx.TransportError as exc:
                last_error = MaxApiNetworkError(str(exc))
                if attempt >= self._retries:
                    raise last_error from exc
                await asyncio.sleep(2**attempt)
                continue

            if response.status_code not in RETRY_STATUSES:
                return self._decode_response(response)

            last_error = MaxApiServerError(
                f"MAX API temporary failure: {response.status_code}",
                status_code=response.status_code,
                payload=self._safe_json(response),
            )
            if attempt >= self._retries:
                raise last_error
            await asyncio.sleep(self._retry_delay(response, attempt))

        raise last_error or MaxApiError("MAX API request failed")

    def _decode_response(self, response: httpx.Response) -> JsonDict:
        payload = self._safe_json(response)
        if 200 <= response.status_code < 300:
            if isinstance(payload, dict) and payload.get("success") is False:
                raise MaxApiClientError(
                    "MAX API returned success=false",
                    status_code=response.status_code,
                    payload=payload,
                )
            return payload if isinstance(payload, dict) else {"data": payload}
        error_cls: type[MaxApiError]
        if response.status_code == 401:
            error_cls = MaxApiAuthError
        elif 400 <= response.status_code < 500:
            error_cls = MaxApiClientError
        else:
            error_cls = MaxApiServerError
        raise error_cls(
            f"MAX API returned {response.status_code}",
            status_code=response.status_code,
            payload=payload,
        )

    @staticmethod
    def _message_payload(body: NewMessageBody | JsonDict | str) -> JsonDict:
        if isinstance(body, NewMessageBody):
            return body.to_payload()
        if isinstance(body, str):
            return {"text": body}
        return body

    @staticmethod
    def _safe_json(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            if retry_after.isdigit():
                return min(float(retry_after), 30.0)
            try:
                retry_at = parsedate_to_datetime(retry_after).timestamp()
                return min(max(retry_at - time.time(), 0.0), 30.0)
            except (TypeError, ValueError, OverflowError):
                pass
        return min(float(2**attempt), 30.0)
