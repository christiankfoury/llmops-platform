# Deployment

## Environments

The project targets four environments:

- local
- dev
- staging
- prod

## Local deployment

Target local stack:

```text
Docker Compose:
- API
- Web
- PostgreSQL
- Redis
```

Expected command after implementation:

```bash
docker compose up --build
```

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
