COMPOSE ?= docker compose
PYTHON ?= PYTHONPATH=src UV_CACHE_DIR=.uv-cache uv run python

.PHONY: build up down restart logs ps migrate seed-demo validate-data import-data test test-unit test-integration lint format typecheck max-smoke webhook-register webhook-list webhook-delete production-setup

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) run --rm migrate

seed-demo:
	$(PYTHON) -m navigator.infrastructure.data.seed

validate-data:
	$(PYTHON) -m navigator.infrastructure.data.import_measures --file data/measures.example.csv --validate-only

import-data:
	$(PYTHON) -m navigator.infrastructure.data.import_measures --file data/measures.csv --apply

test:
	$(PYTHON) -m pytest

test-unit:
	$(PYTHON) -m pytest tests/unit

test-integration:
	$(PYTHON) -m pytest tests/integration

lint:
	$(PYTHON) -m ruff check src

format:
	$(PYTHON) -m ruff format src tests

typecheck:
	$(PYTHON) -m mypy src

max-smoke:
	$(PYTHON) -m navigator.entrypoints.max_smoke

webhook-register:
	$(PYTHON) -m navigator.entrypoints.webhook register

webhook-list:
	$(PYTHON) -m navigator.entrypoints.webhook list

webhook-delete:
	$(PYTHON) -m navigator.entrypoints.webhook delete

production-setup:
	./scripts/production-setup.sh
