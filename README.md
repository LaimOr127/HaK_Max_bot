# Навигатор льгот и субсидий для MAX

Bot-first MVP для MAX: предприниматель вводит ИНН или заполняет профиль вручную,
получает подходящие меры поддержки, добавляет их в чек-лист и может сравнить две
меры в miniapp.

Проект уже содержит backend, MAX-бота, static miniapp, импорт каталога, миграции,
Docker Compose для локального и production запуска.

## Что работает

- MAX-бот: `/start`, `/help`, `/profile`, `/checklist`, `/reset`.
- Онбординг по ИНН с FNS/RMSP enrichment и ручным fallback.
- Ручные кнопки профиля: форма бизнеса, сфера, стадия, сотрудники.
- Детерминированный подбор мер по региону, сфере, форме, стадии, МСП и сотрудникам.
- Карточки мер, подробности, чек-лист документов, feedback по мере.
- Miniapp: мобильный онбординг по ИНН или вручную, подтверждение профиля,
  персональный подбор, карточки мер, сравнение и чек-лист.
- Polling для локальной разработки и webhook для production.
- Alembic migrations, PostgreSQL, Redis, Caddy HTTPS в production.

## Быстрый локальный запуск

Требования: Docker Compose v2, Python 3.12 и `uv` для локальных команд без Docker.

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`compose.yml` поднимает `postgres`, `redis`, `migrate`, `catalog`, `bot` и
`worker`. Docker Compose v2 сам видит файл `compose.yml`, поэтому флаг `-f` для
локального запуска не нужен.

Если нужен локальный Python workflow:

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra dev
make test
make lint
make typecheck
```

## Основные команды

| Команда | Что делает |
| --- | --- |
| `make up` | Собирает и запускает локальный Compose stack |
| `make down` | Останавливает локальный stack |
| `make logs` | Показывает логи сервисов |
| `make ps` | Показывает состояние контейнеров |
| `make migrate` | Запускает Alembic migrations |
| `make seed-demo` | Загружает справочники, demo-каталог и current-каталог |
| `make validate-data` | Валидирует `data/measures.example.csv` |
| `make import-data` | Импортирует `data/measures.csv`, если файл добавлен |
| `make max-smoke` | Проверяет текущий `MAX_BOT_TOKEN` |
| `make webhook-register` | Регистрирует webhook в MAX |
| `make webhook-list` | Показывает webhook subscriptions |
| `make webhook-delete` | Удаляет webhook subscription |

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните только то, что нужно для режима.
Секреты не коммитятся.

| Переменная | Когда нужна | Назначение |
| --- | --- | --- |
| `APP_ENV` | всегда | `local`, `test` или `production` |
| `DATABASE_URL` | всегда | Async SQLAlchemy URL PostgreSQL |
| `REDIS_URL` | всегда | Redis URL для cache/idempotency |
| `MAX_BOT_TOKEN` | для реального бота | Токен MAX-бота |
| `MAX_TRANSPORT` | всегда | `polling` локально, `webhook` в production |
| `MAX_WEBHOOK_PUBLIC_URL` | webhook | Публичный HTTPS origin, например `https://example.ru` |
| `MAX_WEBHOOK_PUBLIC_HOST` | Caddy | Домен для Caddy virtual host |
| `MAX_WEBHOOK_SECRET` | webhook | Секрет заголовка `X-Max-Bot-Api-Secret` |
| `FNS_PROVIDER` | опционально | `rmsp_portal`, `local_snapshot` или `mock` |
| `OPENROUTER_ENABLED` | опционально | Включает LLM explanation fallback |
| `MINIAPP_ENABLED` | miniapp | Включает open_app-кнопки и API miniapp |
| `MINIAPP_COMPARE_URL` | miniapp | URL miniapp, сейчас используется как feature guard |
| `REMINDERS_ENABLED` | worker | Включает напоминания по дедлайнам |
| `CADDY_EMAIL` | production | Email для Let's Encrypt |

`Settings` валидирует опасные комбинации: webhook требует `MAX_BOT_TOKEN`,
`MAX_WEBHOOK_PUBLIC_URL` и `MAX_WEBHOOK_SECRET`; miniapp требует
`MINIAPP_COMPARE_URL`; OpenRouter требует ключ и модель.

## Интеграция с MAX

Локально используйте polling:

```env
MAX_TRANSPORT=polling
MAX_BOT_TOKEN=<token>
MINIAPP_ENABLED=false
```

В production используйте webhook:

```env
APP_ENV=production
MAX_TRANSPORT=webhook
MAX_BOT_TOKEN=<token>
MAX_WEBHOOK_PUBLIC_URL=https://<domain>
MAX_WEBHOOK_PUBLIC_HOST=<domain>
MAX_WEBHOOK_SECRET=<random-secret>
MINIAPP_ENABLED=true
MINIAPP_COMPARE_URL=https://<domain>/miniapp
```

MAX API вызывается через `https://platform-api2.max.ru` с raw заголовком
`Authorization: <MAX_BOT_TOKEN>`. Webhook принимает оба пути:
`POST /webhook/max` и `POST /webhooks/max`.

## Miniapp

Публичная страница:

- `GET /miniapp`
- `GET /miniapp/compare`

API miniapp:

- `GET /api/miniapp/home`
- `POST /api/miniapp/lookup` — поиск по ИНН через настроенный FNS provider
- `POST /api/miniapp/manual` — новый ручной профиль
- `POST /api/miniapp/profile` — уточнение или исправление полей профиля
- `POST /api/miniapp/confirm` — подтверждение полного профиля
- `GET /api/miniapp/measures/{measure_id}` — подробности рекомендованной меры
- `GET /api/miniapp/compare?ids=<uuid>,<uuid>`
- `POST /api/miniapp/checklist/{measure_id}`
- `DELETE /api/miniapp/checklist/{measure_id}`

Все API miniapp требуют заголовок `X-Max-Init-Data`. Backend проверяет подпись
MAX Bridge init data через `MAX_BOT_TOKEN`, срок действия `auth_date` и
`start_param` для comparison launch.

Чтобы miniapp открывался из MAX:

1. Опубликуйте backend по HTTPS.
2. Укажите `https://<domain>/miniapp` в настройках бота/miniapp MAX.
3. Включите `MINIAPP_ENABLED=true`.
4. Укажите `MINIAPP_COMPARE_URL=https://<domain>/miniapp`.
5. Перезапустите `bot`.

Без регистрации публичного HTTPS URL MAX не сможет открыть miniapp и передать
подписанный init data. Сам API включается переменной `MINIAPP_ENABLED`, но
защищенные методы принимают только валидный `X-Max-Init-Data`. Основной chat
flow остается рабочим.

Экран взят из переданного прототипа MAX.make: старт, ввод ИНН и проверка
профиля повторяют мобильный макет. Примерные компании и меры из прототипа не
используются: данные поступают из FNS provider, профиля и каталога PostgreSQL.
Основной ОКВЭД сопоставляется со сферой по `data/okved_mapping.csv`.
Если ФНС не ответила, пользователь может заполнить профиль вручную. После
подтверждения недостающие сфера, стаж и численность запрашиваются в miniapp;
при пустом каталоге интерфейс честно показывает отсутствие подходящих мер.

## Каталог мер

Данные лежат в `data/`.

- `measures.example.csv` содержит synthetic demo-меры для локальной разработки.
- `measures.current.csv` содержит curated меры для production/MVP.
- `sphere_categories.csv` и `okved_mapping.csv` нужны для профиля и маппинга ОКВЭД.
- `courses.example.csv` сидится как справочник курсов.

Локально `catalog` импортирует demo plus current данные. В `APP_ENV=production`
demo-меры отключаются, и импортируется только `measures.current.csv`.

Валидация CSV:

```bash
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m navigator.infrastructure.data.import_measures --file data/measures.example.csv --validate-only
PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python -m navigator.infrastructure.data.import_measures --file data/measures.current.csv --validate-only
```

## Production deploy

Production Compose запускается так:

```bash
docker compose -f compose.yml -f compose.prod.yml up -d --build
```

`compose.prod.yml` включает webhook mode, Caddy, скрывает порты PostgreSQL/Redis
и включает reminder worker.

Для подготовленного VPS можно использовать script:

```bash
git clone https://github.com/LaimOr127/HaK_Max_bot.git benefit-navigator
cd benefit-navigator
./scripts/production-setup.sh
```

Script:

- требует запуск от `root`;
- ожидает, что домен из `MAX_WEBHOOK_PUBLIC_HOST` резолвится в `EXPECTED_PUBLIC_IP`;
- спрашивает `MAX_BOT_TOKEN` и `CADDY_EMAIL`;
- генерирует `POSTGRES_PASSWORD` и `MAX_WEBHOOK_SECRET`;
- создает `.env` с правами `0600`;
- запускает production Compose;
- проверяет `https://<domain>/health/ready`;
- запускает MAX smoke-check и регистрирует webhook.

Укажите домен и IP сервера самого бота перед запуском. Script не содержит
доменов других проектов по умолчанию:

```bash
MAX_WEBHOOK_PUBLIC_HOST=example.ru EXPECTED_PUBLIC_IP=203.0.113.10 ./scripts/production-setup.sh
```

## Проверка после запуска

```bash
docker compose ps
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Для production:

```bash
docker compose -f compose.yml -f compose.prod.yml ps
curl https://<domain>/health/live
curl https://<domain>/health/ready
```

Для smoke-check MAX:

```bash
make max-smoke
```

## Ограничения

- Рекомендации не являются юридическим решением о праве на меру.
- FNS/RMSP enrichment best-effort; ручное заполнение профиля обязательно должно
  оставаться рабочим fallback.
- OpenRouter выключен по умолчанию и не принимает решения о eligibility.
- Miniapp открывается из MAX только при публичном HTTPS URL, регистрации в MAX
  и валидном `X-Max-Init-Data`.
- Current production-каталог сейчас небольшой: расширение идет через CSV и
  повторную валидацию источников.

Подробная схема системы описана в `ARCHITECTURE.md`.
