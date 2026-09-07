API_PYTHON ?= .venv/Scripts/python
NPM ?= npm
MVNW ?= apps/api-java/mvnw

.PHONY: check docker-build-prod local-up local-down local-logs api-verify api-migrate api-seed api-test python-reference-check python-reference-up web-lint web-test web-typecheck

check: api-verify web-lint web-typecheck web-test

api-verify:
	$(MVNW) --batch-mode --no-transfer-progress --strict-checksums -f apps/api-java/pom.xml clean verify

api-test: api-verify

docker-build-prod:
	docker build -f apps/api-java/Dockerfile --target api -t production-ai-platform-api:prod .
	docker build -f apps/api-java/Dockerfile --target migration -t production-ai-platform-migration:prod .
	docker build -f apps/web/Dockerfile -t production-ai-platform-web:prod apps/web

local-up:
	docker compose up --build

local-down:
	docker compose down

local-logs:
	docker compose logs -f api migration web postgres redis

api-migrate:
	docker compose run --rm migration

api-seed:
	docker compose run --rm migration java -jar /app/migration.jar seed-local

python-reference-up:
	docker compose -f docker-compose.python-reference.yml up --build

python-reference-check:
	$(API_PYTHON) -m ruff check apps/api
	$(API_PYTHON) -m ruff format --check apps/api
	$(API_PYTHON) -m pytest

web-lint:
	cd apps/web && $(NPM) run lint

web-typecheck:
	cd apps/web && $(NPM) run typecheck

web-test:
	cd apps/web && $(NPM) run test
