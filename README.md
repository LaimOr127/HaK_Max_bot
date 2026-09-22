# Навигатор льгот и субсидий

Bot-first MVP for MAX: a small-business owner answers a short dialog, gets 1-3 suitable support measures, saves one to a checklist, and tracks documents later.

Mini-app work is intentionally deferred until the bot acceptance path works end to end.

```mermaid
flowchart TD
    MAX[MAX User] --> MAXAPI[MAX Platform]
    MAXAPI --> BOT[Bot/API Container]
    BOT --> APP[Application Services]
    APP --> MATCH[Deterministic Matching]
    APP --> DB[(PostgreSQL)]
    APP --> REDIS[(Redis)]
    APP --> FNS[FNS Adapter]
    APP --> EXPLAIN[Explanation Provider]
    FNS --> RMSP[Public FNS/RMSP source]
    EXPLAIN --> TEMPLATE[Template]
    EXPLAIN -. feature flag .-> OR[OpenRouter]
    WORKER[Worker Container] --> DB
    WORKER --> MAXAPI
    CADDY[Caddy HTTPS] --> BOT
    MINI[Future Mini App] -. later .-> BOT
```

## Quick Start

```bash
cp .env.example .env
docker compose up -d --build
make seed-demo
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Local compose starts PostgreSQL, Redis, migrations, the API/bot, and the reminder worker. MAX polling is configured through `MAX_TRANSPORT=polling`; real MAX calls require `MAX_BOT_TOKEN`. For local Python checks, run `uv sync --extra dev` once.

## Commands

- `make build`, `make up`, `make down`, `make restart`, `make logs`, `make ps` wrap Compose.
- `make migrate` runs Alembic.
- `make lint`, `make format`, `make typecheck`, `make test` run local quality checks.
- `make seed-demo` loads the included demo catalogue; `make validate-data` and `make import-data` validate/import a curated CSV.
- `make max-smoke` checks the configured MAX token; `make webhook-register`, `make webhook-list`, and `make webhook-delete` manage subscriptions.

## Environment

Secrets live only in `.env` or deployment secret storage. `.env.example` contains placeholders for PostgreSQL, Redis, MAX, FNS, OpenRouter, mini-app, reminders, and debug toggles.

OpenRouter is off by default and must never decide eligibility. Measures and courses are manually curated data, not a live МСП.РФ API. FNS is best-effort profile enrichment with a manual dialog fallback.

## External Contracts

- MAX API base URL is `https://platform-api2.max.ru`. Requests use raw `Authorization: <MAX_BOT_TOKEN>`, never token query parameters.
- MAX webhook requests are authenticated with `X-Max-Bot-Api-Secret`. The webhook handler must respond `200` within 30 seconds; duplicate delivery must return `200` without repeated side effects.
- FNS enrichment uses the official SME open dataset at `https://www.nalog.gov.ru/opendata/7707329152-rsmp/` plus public search. There is no documented official per-INN REST API in scope.
- Any internal `search-proc.json` endpoint is best-effort only; the product must keep manual fallback.
- OpenRouter uses `/api/v1/chat/completions` with Bearer auth, provider `ZDR`, and data collection disabled; it remains disabled by default.

## Migrations

Alembic owns schema changes:

```bash
docker compose run --rm migrate
```

The initial migration creates all core persistence tables from the specification.

## Production

Production combines local and prod files:

```bash
docker compose -f compose.yml -f compose.prod.yml up -d --build
```

`compose.prod.yml` switches MAX to webhook mode, adds Caddy, and does not publish PostgreSQL or Redis ports. Fill `MAX_WEBHOOK_PUBLIC_URL`, `MAX_WEBHOOK_SECRET`, and real secrets before deploy.

For the configured VPS, create an A record for `svadba-2026.ru` pointing to `193.5.251.40`, clone this repository, then run as `root`:

```bash
git clone https://github.com/LaimOr127/HaK_Max_bot.git benefit-navigator
cd benefit-navigator
./scripts/production-setup.sh
```

The script securely prompts only for `MAX_BOT_TOKEN` and `CADDY_EMAIL`, generates all other runtime secrets in the ignored `.env`, starts production Compose, checks HTTPS health, verifies the MAX token, and registers the webhook.

## Known Limitations

The bot path is implemented: onboarding, deterministic recommendations, details, checklists, feedback, investor lead capture, webhook/polling transport, idempotency, import, and reminders. A real MAX token and a running Docker daemon are still needed for an external smoke test; Mini App work is deliberately deferred.
