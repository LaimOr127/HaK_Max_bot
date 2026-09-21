from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from navigator.application.reminders import ReminderService
from navigator.config import get_settings
from navigator.infrastructure.db.repositories import SqlAlchemyReminderRepository
from navigator.infrastructure.fns.local_snapshot import LocalSnapshotCompanyLookup
from navigator.infrastructure.fns.mock import MockCompanyLookup
from navigator.infrastructure.fns.rmsp_portal import RmspPortalCompanyLookup
from navigator.infrastructure.max_api.client import MaxApiClient
from navigator.infrastructure.max_api.gateway import MaxApiGateway
from navigator.infrastructure.observability.logging import configure_logging
from navigator.infrastructure.redis.idempotency import RedisIdempotencyStore
from navigator.presentation.maxbot.runtime import BotRuntime, SystemClock, polling_loop

settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    company_lookup = _company_lookup()
    max_client = None
    polling_task = None

    app.state.db_engine = engine
    app.state.redis = redis
    app.state.bot_runtime = None

    if settings.max_bot_token is not None:
        max_client = MaxApiClient(
            settings.max_bot_token.get_secret_value(),
            base_url=str(settings.max_api_base_url),
            timeout_seconds=settings.max_http_timeout_seconds,
        )
        app.state.bot_runtime = BotRuntime(
            sessionmaker=sessionmaker,
            max_client=max_client,
            company_lookup=company_lookup,
        )
        if settings.max_transport == "polling":
            polling_task = asyncio.create_task(
                polling_loop(app.state.bot_runtime, max_client, settings.max_poll_timeout_seconds)
            )
            log.info("MAX polling started")

    try:
        yield
    finally:
        if polling_task is not None:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        if max_client is not None:
            await max_client.aclose()
        if hasattr(company_lookup, "aclose"):
            await company_lookup.aclose()
        await redis.aclose()
        await engine.dispose()


app = FastAPI(title="Benefit Navigator", version="0.1.0", lifespan=lifespan)


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready() -> dict[str, str]:
    async with app.state.db_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await app.state.redis.ping()
    return {"status": "ready"}


@app.post("/webhook/max")
@app.post("/webhooks/max")
async def max_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
) -> dict[str, str]:
    expected = settings.max_webhook_secret
    if (
        expected is None
        or x_max_bot_api_secret is None
        or not hmac.compare_digest(x_max_bot_api_secret, expected.get_secret_value())
    ):
        raise HTTPException(status_code=401, detail="invalid webhook secret")
    runtime = request.app.state.bot_runtime
    if runtime is None:
        raise HTTPException(status_code=503, detail="MAX bot token is not configured")
    try:
        update = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="update must be an object")
    event_id = str(update.get("update_id") or update.get("id") or _update_hash(update))
    idempotency = RedisIdempotencyStore(request.app.state.redis, prefix="max-update")
    if not await idempotency.mark_once(event_id, 86400):
        return {"status": "duplicate"}
    try:
        await runtime.process_update(update)
    except Exception:
        await idempotency.release(event_id)
        raise
    return {"status": "ok"}


async def _worker_loop() -> None:
    if settings.max_bot_token is None:
        await asyncio.Event().wait()
        return
    if not settings.reminders_enabled:
        await asyncio.Event().wait()
        return
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    client = MaxApiClient(
        settings.max_bot_token.get_secret_value(),
        base_url=str(settings.max_api_base_url),
        timeout_seconds=settings.max_http_timeout_seconds,
    )
    try:
        while True:
            async with sessionmaker() as session:
                service = ReminderService(
                    SqlAlchemyReminderRepository(session), MaxApiGateway(client), SystemClock()
                )
                for days_before in settings.reminder_days:
                    await service.send_due(days_before)
                await session.commit()
            await asyncio.sleep(settings.reminder_scan_interval_seconds)
    finally:
        await client.aclose()
        await engine.dispose()


def _company_lookup() -> RmspPortalCompanyLookup | LocalSnapshotCompanyLookup | MockCompanyLookup:
    if settings.fns_provider == "local_snapshot":
        return LocalSnapshotCompanyLookup(ROOT / "data" / "companies.csv")
    if settings.fns_provider == "mock":
        return MockCompanyLookup({})
    return RmspPortalCompanyLookup(timeout_seconds=settings.fns_timeout_seconds)


def _update_hash(update: dict[str, object]) -> str:
    encoded = json.dumps(update, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-placeholder", action="store_true")
    parser.add_argument("--importer-placeholder", action="store_true")
    args = parser.parse_args()
    if args.worker_placeholder or args.importer_placeholder:
        asyncio.run(_worker_loop())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
