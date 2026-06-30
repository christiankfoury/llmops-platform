.PHONY: local-up local-down local-logs api-migrate api-seed api-test web-lint web-typecheck

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

api-test:
	cd apps/api && python -m pytest

web-lint:
	cd apps/web && npm run lint

web-typecheck:
	cd apps/web && npm run typecheck
