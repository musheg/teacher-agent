.PHONY: help up down logs migrate seed lint fmt test check sync dev rebuild

help:
	@echo "Targets:"
	@echo "  make sync       — uv sync (install Python deps)"
	@echo "  make up         — docker compose up -d (api, frontend, postgres, redis)"
	@echo "  make down       — docker compose down"
	@echo "  make rebuild    — docker compose build --no-cache"
	@echo "  make logs       — tail logs"
	@echo "  make migrate    — run alembic upgrade head"
	@echo "  make seed       — seed initial age band + math course"
	@echo "  make lint       — ruff + mypy"
	@echo "  make fmt        — ruff format"
	@echo "  make test       — pytest"
	@echo "  make check      — lint + test"
	@echo "  make dev        — local dev (npm run dev)"

sync:
	uv sync

up:
	docker compose up -d --build

down:
	docker compose down

rebuild:
	docker compose build --no-cache

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose --profile migrate up --build alembic

seed:
	docker compose run --rm api python -m app.scripts.seed

lint:
	uv run ruff check app
	uv run mypy app

fmt:
	uv run ruff format app
	uv run ruff check --fix app

test:
	uv run pytest -q

check: lint test

dev:
	npm run dev
