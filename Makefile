API_PYTHON ?= .venv/Scripts/python
NPM ?= npm

.PHONY: check docker-build-prod local-up local-down local-logs api-format-check api-lint api-migrate api-seed api-test web-lint web-test web-typecheck

check: api-lint api-format-check api-test web-lint web-typecheck web-test

docker-build-prod:
	docker build -f apps/api/Dockerfile -t production-ai-platform-api:prod apps/api
	docker build -f apps/web/Dockerfile -t production-ai-platform-web:prod apps/web

local-up:
	docker compose up --build

local-down:
	docker compose down

local-logs:
	docker compose logs -f api web postgres redis

api-migrate:
	docker compose exec api alembic upgrade head

api-seed:
	docker compose exec api python -m scripts.seed_dev_data

api-lint:
	$(API_PYTHON) -m ruff check apps/api

api-format-check:
	$(API_PYTHON) -m ruff format --check apps/api

api-test:
	$(API_PYTHON) -m pytest

web-lint:
	cd apps/web && $(NPM) run lint

web-typecheck:
	cd apps/web && $(NPM) run typecheck

web-test:
	cd apps/web && $(NPM) run test
