from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .template import build_explanation_messages, fallback_explanation

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        *,
        base_url: str = OPENROUTER_BASE_URL,
        timeout_seconds: float = 12.0,
        enabled: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._enabled = enabled and bool(api_key and model)
        self._model = model
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers=(
                {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                if api_key
                else {}
            ),
        )

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def chat(self, messages: list[dict[str, str]], *, max_tokens: int = 180) -> str | None:
        if not self._enabled or self._model is None:
            return None
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
            "provider": {"zdr": True, "data_collection": "deny"},
        }
        for attempt in range(2):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                if attempt:
                    return None
                await asyncio.sleep(0.5)
                continue
            return content.strip() if isinstance(content, str) and content.strip() else None
        return None

    async def explain_measure(
        self,
        measure_title: str,
        profile_summary: str,
        facts: list[str],
    ) -> str:
        messages = build_explanation_messages(measure_title, profile_summary, facts)
        return await self.chat(messages) or fallback_explanation(measure_title)
