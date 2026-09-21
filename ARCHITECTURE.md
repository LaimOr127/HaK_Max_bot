# Architecture

The project is a modular monolith. Runtime is simple: one bot/API container, one worker container, PostgreSQL as source of truth, Redis for short-lived operational state, and Caddy only in production.

Layering target:

```text
presentation -> application -> domain
                 application -> ports
infrastructure implements ports
```

Foundation decisions:

- SQLAlchemy models live under `infrastructure/db` and are exposed to Alembic through one shared `Base.metadata`.
- Health is intentionally separate from MAX/FNS/OpenRouter: readiness checks PostgreSQL and Redis only.
- Local mode may start without a MAX token so infrastructure can be tested before real integration. Webhook/OpenRouter/mini-app settings fail fast only when those features are enabled.
- Redis loss must not delete profile, checklist, measures, feedback, or conversation state; those are PostgreSQL-backed.
- MAX integration target is `https://platform-api2.max.ru` with raw `Authorization`. Webhook auth uses `X-Max-Bot-Api-Secret`, and production handlers must finish within 30 seconds with idempotent `200` responses.
- FNS profile enrichment is based on the official SME open dataset and public search. Internal search endpoints are treated as best-effort, not as stable contracts.
- OpenRouter is a template-only explanation fallback: `/api/v1/chat/completions`, Bearer auth, provider `ZDR`, `data_collection=deny`, and no eligibility decisions.

Later slices must keep SQL/HTTP out of handlers and route side effects through application services and ports.
