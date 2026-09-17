# Local setup and deployment boundaries

## Local deployment

Use Docker with Compose v2. From the repository root:

```sh
docker compose up --build
```

The default project starts PostgreSQL and Redis, runs the Flyway migration container,
then starts Java and the web application. The synthetic dashboard is available at
`http://localhost:3000`; API readiness is `http://localhost:8000/health/ready`.
No cloud or LLM credentials are needed. Seed keys and database passwords are local
placeholders; do not reuse them in a shared environment.

| Service | Default host address | Configuration |
|---|---|---|
| Web | 127.0.0.1:3000 | `WEB_PORT` |
| Java API | 127.0.0.1:8000 | `API_PORT` |
| PostgreSQL | 127.0.0.1:55432 | `POSTGRES_PORT` |
| Redis | 127.0.0.1:56379 | `REDIS_PORT` |

If a port is occupied, set the corresponding variable in your shell before starting.
Use `docker compose ps -a` and `docker compose logs migration api` to diagnose startup.
The migration job must finish successfully. Do not work around failures by enabling
application-owned migrations or removing existing data.

Use the mock request in the [README](../README.md) to exercise the API. It writes to
PostgreSQL; the default synthetic dashboard intentionally stays fixed. For real usage
views, follow [OIDC setup and grants](java-operator-security.md). Management metrics
are private on container port 9080; the default Compose setup does not publish that port.

Stop without removing data:

```sh
docker compose stop
```

Do not use `down -v` as routine cleanup. A separate Compose project creates independent
volumes and is appropriate for an isolated local rehearsal. Existing data stays intact.

## Production image builds

```sh
docker build --target api -f apps/api-java/Dockerfile -t production-ai-platform-api:local .
docker build --target migration -f apps/api-java/Dockerfile -t production-ai-platform-migration:local .
docker build -f apps/web/Dockerfile -t production-ai-platform-web:local apps/web
```

The images run non-root. CI validates the actual container stack, data-service TLS,
runtime images and immutable registry promotion. [Testing](testing.md)

## AWS deployment

AWS has not been deployed. The [launch checklist](aws-launch-checklist.md) covers
account/access setup, private runners, state/bootstrap, secrets, identity, costs,
monitoring prerequisites and approval. Terraform/Helm configuration alone is not a
validated cloud deployment. Monitoring remains [blocked](security/monitoring-vulnerability-backlog.md).

The release workflows are manual and held. Once separately approved, they require
current exact-revision CI, immutable images/charts, schema compatibility and protected
publisher/migration/application jobs. Use the [immutable release runbook](immutable-release-runbook.md);
do not invoke historical SHA-tag deployment examples from the archive.

Rollback selects a previously verified compatible application release. It never
downgrades a database. AWS cleanup, real DNS/TLS, public access and data deletion need
separate approval. Staging/prod deployments remain optional and untested in AWS.
