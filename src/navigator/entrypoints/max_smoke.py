from __future__ import annotations

import asyncio

from navigator.config import get_settings
from navigator.infrastructure.max_api.client import MaxApiClient
from navigator.infrastructure.max_api.errors import MaxApiAuthError


async def smoke() -> None:
    settings = get_settings()
    if settings.max_bot_token is None:
        raise SystemExit("MAX_BOT_TOKEN is empty")
    try:
        async with MaxApiClient(
            settings.max_bot_token.get_secret_value(),
            base_url=str(settings.max_api_base_url),
            timeout_seconds=settings.max_http_timeout_seconds,
        ) as client:
            payload = await client.get_me()
    except MaxApiAuthError as exc:
        raise SystemExit("MAX auth failed: check MAX_BOT_TOKEN") from exc
    print(payload)


def main() -> None:
    asyncio.run(smoke())


if __name__ == "__main__":
    main()
