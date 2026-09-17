# Operations runbook

These commands target the default local Java stack. AWS and the monitoring release
remain blocked; Kubernetes procedures require the approved environment and context.

## Start with health and recent changes

```sh
docker compose ps
curl http://localhost:8000/health/ready
docker compose logs --tail=100 api migration web
```

Confirm the expected image revision, migration exit status and PostgreSQL/Redis
health. The web container can show synthetic examples even when the API is down;
use API readiness to assess backend health. Management metrics use the private
management listener; do not expose it as an unauthenticated public endpoint.

## Common failures

| Symptom | Investigation and response |
|---|---|
| API fails startup | Inspect migration logs, database connectivity and schema validation. Flyway is the sole migration owner; never enable automatic schema updates or downgrade history. |
| Readiness fails | Check PostgreSQL and Redis. Both are required. Restore the dependency and confirm recovery before returning traffic. |
| Increased errors or latency | Correlate request IDs, safe error categories, limits and recent changes. Check dependency health and bounded provider deadlines; the current provider is a mock. |
| Operator sees 401/403 | Check configured OIDC issuer/audience, session and project grants. Application keys do not confer operator access. Do not disable authorization. |
| Dashboard appears unchanged | The default read-only demo uses fixed fixtures. Configure operator sign-in to inspect stored API usage. |
| Release verification fails | Inspect the failed job and artifact provenance. Fix the cause; do not borrow evidence from another revision or bypass checks. |

Never paste tokens, request content, credentials or raw provider payloads into an
issue or incident log. Monitoring prototype dashboards are not evidence that the
current monitoring release is deployable.

## Recovery and rollback

Use the [local recovery rehearsal](local-recovery-rehearsal.md) for the tested
dependency outage, restart and compatible rollback procedure. Use
[backup and restore](backup-restore.md) to restore into a separate target and
verify rows before any approved cutover. Do not overwrite the source database.

For an approved AWS environment, follow the [immutable release runbook](immutable-release-runbook.md),
verify cluster/namespace and immutable image provenance, and use a schema-compatible
previous application release. Rollback never means a destructive schema downgrade.
Do not run apply, destroy, public routing or secret changes without their approval.

`docker compose stop` stops local services while retaining database volumes.

See [incident response](incident-response.md), [Java reliability](java-reliability.md)
and the [historical runbook](archive/runbook-baseline.md) for supporting context.
