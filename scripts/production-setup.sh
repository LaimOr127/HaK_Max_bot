#!/usr/bin/env bash
set -Eeuo pipefail

DOMAIN="${MAX_WEBHOOK_PUBLIC_HOST:-svadba-2026.ru}"
EXPECTED_IP="${EXPECTED_PUBLIC_IP:-193.5.251.40}"
COMPOSE=(docker compose -f compose.yml -f compose.prod.yml)

die() {
    echo "ERROR: $*" >&2
    exit 1
}

prompt() {
    local name="$1" value="${!1:-}"
    if [[ -z "$value" ]]; then
        read -r -p "$name: " value
    fi
    [[ -n "$value" ]] || die "$name is required"
    printf -v "$name" '%s' "$value"
}

prompt_secret() {
    local name="$1" value="${!1:-}"
    if [[ -z "$value" ]]; then
        read -r -s -p "$name: " value
        echo >&2
    fi
    [[ -n "$value" ]] || die "$name is required"
    printf -v "$name" '%s' "$value"
}

[[ $EUID -eq 0 ]] || die "run as root"
[[ -f compose.yml && -f compose.prod.yml ]] || die "run from the repository root"
[[ ! -e .env ]] || die ".env already exists; keep its secrets and run Docker Compose directly"

if ! command -v docker >/dev/null; then
    apt-get update
    apt-get install -y docker.io docker-compose-v2 openssl curl
    systemctl enable --now docker
fi

command -v openssl >/dev/null || die "openssl is required"
docker compose version >/dev/null || die "Docker Compose v2 is required"

resolved_ip="$(getent ahostsv4 "$DOMAIN" | awk 'NR == 1 {print $1}')"
[[ "$resolved_ip" == "$EXPECTED_IP" ]] || die "$DOMAIN must resolve to $EXPECTED_IP (got: ${resolved_ip:-none})"

prompt_secret MAX_BOT_TOKEN
prompt CADDY_EMAIL

POSTGRES_PASSWORD="$(openssl rand -hex 32)"
MAX_WEBHOOK_SECRET="$(openssl rand -hex 32)"
umask 077
cat >.env <<EOF
APP_ENV=production
LOG_LEVEL=INFO
POSTGRES_DB=benefit_navigator
POSTGRES_USER=benefit
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql+asyncpg://benefit:$POSTGRES_PASSWORD@postgres:5432/benefit_navigator
REDIS_URL=redis://redis:6379/0
MAX_API_BASE_URL=https://platform-api2.max.ru
MAX_BOT_TOKEN=$MAX_BOT_TOKEN
MAX_TRANSPORT=webhook
MAX_WEBHOOK_PUBLIC_URL=https://$DOMAIN
MAX_WEBHOOK_PUBLIC_HOST=$DOMAIN
MAX_WEBHOOK_SECRET=$MAX_WEBHOOK_SECRET
MAX_POLL_TIMEOUT_SECONDS=30
MAX_HTTP_TIMEOUT_SECONDS=10
FNS_PROVIDER=rmsp_portal
FNS_LOOKUP_ENABLED=true
FNS_TIMEOUT_SECONDS=4
FNS_CACHE_TTL_SECONDS=21600
FNS_LOOKUP_LIMIT_10M=5
FNS_LOOKUP_LIMIT_1H=30
OPENROUTER_ENABLED=false
MINIAPP_ENABLED=false
REMINDERS_ENABLED=true
REMINDER_DAYS=[7,3,1]
REMINDER_SCAN_INTERVAL_SECONDS=600
DEBUG_ENDPOINTS_ENABLED=false
CADDY_EMAIL=$CADDY_EMAIL
EOF

"${COMPOSE[@]}" up -d --build
for _ in {1..30}; do
    if curl --fail --silent --show-error "https://${DOMAIN}/health/ready" >/dev/null; then
        "${COMPOSE[@]}" exec -T bot python -m navigator.entrypoints.max_smoke
        "${COMPOSE[@]}" exec -T bot python -m navigator.entrypoints.webhook register
        echo "Production deployment is ready: https://${DOMAIN}"
        exit 0
    fi
    sleep 2
done

"${COMPOSE[@]}" ps
"${COMPOSE[@]}" logs --tail=100 caddy bot
die "HTTPS health check did not become ready"
