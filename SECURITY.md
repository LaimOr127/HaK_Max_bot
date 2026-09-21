# Security

Baseline controls:

- Containers run as non-root users.
- Secrets are read from environment variables and `.env` is ignored.
- Production Compose publishes only Caddy ports; PostgreSQL and Redis stay internal.
- Webhook mode requires `MAX_WEBHOOK_PUBLIC_URL` and `MAX_WEBHOOK_SECRET`.
- Health endpoints do not expose secrets or external payloads.
- JSON logs redact common secret/contact fields and avoid raw user messages by default.

Rules for later implementation:

- Use the MAX token only in the `Authorization` header.
- Validate webhook secret before parsing side effects.
- Make callback mutations idempotent and user-owned.
- Do not send personal data or raw FNS payloads to OpenRouter.
- Validate imported source URLs before rendering or storing them.
- Use SQLAlchemy parameters, no dynamic SQL or eval.
