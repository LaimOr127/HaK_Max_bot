from __future__ import annotations

import argparse
import asyncio

from navigator.config import get_settings
from navigator.infrastructure.max_api.client import MaxApiClient


async def _run(command: str) -> None:
    settings = get_settings()
    if settings.max_bot_token is None:
        raise SystemExit("MAX_BOT_TOKEN is empty")
    if settings.max_webhook_public_url is None:
        raise SystemExit("MAX_WEBHOOK_PUBLIC_URL is empty")
    url = f"{str(settings.max_webhook_public_url).rstrip('/')}/webhooks/max"
    async with MaxApiClient(
        settings.max_bot_token.get_secret_value(),
        base_url=str(settings.max_api_base_url),
        timeout_seconds=settings.max_http_timeout_seconds,
    ) as client:
        if command == "register":
            if settings.max_webhook_secret is None:
                raise SystemExit("MAX_WEBHOOK_SECRET is empty")
            result = await client.create_subscription(
                url,
                update_types=["bot_started", "message_created", "message_callback"],
                secret=settings.max_webhook_secret.get_secret_value(),
            )
        elif command == "delete":
            result = await client.delete_subscription(url)
        else:
            result = await client.list_subscriptions()
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("register", "list", "delete"))
    args = parser.parse_args()
    asyncio.run(_run(args.command))


if __name__ == "__main__":
    main()
