.PHONY: local-up local-down local-logs api-test web-lint web-typecheck

local-up:
	docker compose up --build

local-down:
	docker compose down

local-logs:
	docker compose logs -f api web postgres redis

api-test:
	cd apps/api && python -m pytest

web-lint:
	cd apps/web && npm run lint

web-typecheck:
	cd apps/web && npm run typecheck
