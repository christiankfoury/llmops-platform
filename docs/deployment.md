# Deployment

## Environments

The project targets four environments:

- local
- dev
- staging
- prod

## Local deployment

Implemented local stack:

```text
Docker Compose:
- API
- Web
- PostgreSQL
- Redis
```

Start the full stack:

```bash
docker compose up --build
```

The same command is available as:

```bash
make local-up
```

Local service URLs:

- Web dashboard: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/health/ready`
- PostgreSQL host port: `55432`
- Redis host port: `56379`

Stop containers:

```bash
make local-down
```

Local environment examples live in:

- `.env.example`
- `apps/api/.env.example`
- `apps/web/.env.example`

These files use placeholder development values only. Real provider keys, cloud account IDs, and production secrets must not be committed.

## Dev deployment

Dev should deploy automatically from the main branch.

Expected flow:

1. CI validates code.
2. Images are built.
3. Images are pushed to ECR.
4. Helm upgrades dev release.
5. Smoke test runs.

## Staging deployment

Staging should be manually triggered.

Expected flow:

1. Select image tag or commit SHA.
2. Deploy with staging values.
3. Run smoke test.
4. Validate dashboards and logs.

## Production deployment

Production requires approval.

Expected flow:

1. Confirm release notes.
2. Confirm staging validation.
3. Approve production workflow.
4. Deploy with production values.
5. Run smoke test.
6. Monitor dashboards.

## Rollback

Rollback is handled through Helm release history and a dedicated GitHub Actions rollback workflow.

See `docs/runbook.md` and `docs/incident-response.md`.
