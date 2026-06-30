# Testing

Phase 8 adds a local quality baseline for backend and frontend work.

Run the full local check set:

```bash
make check
```

The Makefile defaults to the local Windows virtualenv path `.venv/Scripts/python`. On macOS/Linux, run with an override such as:

```bash
make check API_PYTHON=.venv/bin/python
```

Backend checks:

```bash
make api-lint
make api-format-check
make api-test
```

Frontend checks:

```bash
make web-lint
make web-typecheck
make web-test
```

Docker and migration checks remain phase-specific until CI is introduced:

```bash
docker compose build api web
docker compose exec -T api alembic check
```

The frontend dependency audit currently passes the high/critical gate with:

```bash
npm audit --audit-level=high
```

npm still reports a moderate Next/PostCSS advisory where the automatic fix is a breaking downgrade. Keep this visible until the Next stable line has a non-breaking patched path.
