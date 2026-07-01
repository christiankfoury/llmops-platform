# Security Audit Review

Phase 25 documents audit log review instead of exposing a new production admin endpoint.

## What is logged

The application writes audit records for prompt version and model route configuration changes. Records include:

- actor type
- actor ID
- action
- target type
- target ID
- metadata
- timestamp

Audit logs must not include API key values, provider credentials, database URLs, Redis URLs, or raw secret values.

## Local review

After running migrations and seed data locally, inspect recent audit activity with PostgreSQL:

```bash
docker compose exec -T postgres psql -U ai_platform -d ai_platform \
  -c "select created_at, actor_type, actor_id, action, target_type, target_id from audit_logs order by created_at desc limit 20;"
```

Filter by actor:

```bash
docker compose exec -T postgres psql -U ai_platform -d ai_platform \
  -c "select created_at, action, target_type, target_id from audit_logs where actor_id = 'local-admin' order by created_at desc limit 20;"
```

## Production review path

For dev, staging, and prod, use an approved read-only database access path. Do not print secrets or full metadata blobs into shared tickets or CI logs.

Recommended review fields:

- `created_at`
- `actor_type`
- `actor_id`
- `action`
- `target_type`
- `target_id`

Review metadata only when needed for incident response, and redact sensitive or environment-specific values before sharing.

## Escalation criteria

Escalate to incident response if audit review shows:

- unexpected actor IDs changing prompt versions or model routes
- repeated failed or suspicious admin activity around a release
- configuration changes near a cost spike, latency spike, or elevated error alert
- audit gaps where a known configuration change has no corresponding record

Use `docs/incident-response.md` for severity assignment and `docs/runbook.md` for service triage.
