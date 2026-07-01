# Incident Response

## Severity levels

### SEV1

Critical production outage.

Examples:

- gateway unavailable
- widespread 5xx
- database unavailable
- confirmed data loss or corruption
- secrets exposed

Typical alerts:

- `AIGatewayElevated5xxRate`
- `AIPlatformDatabaseUnavailable`

### SEV2

Major degradation.

Examples:

- high latency
- elevated error rate
- failed deploy with partial impact
- failed migration requiring restore assessment
- cost spike

Typical alerts:

- `AIGatewayHighErrorRate`
- `AIGatewayHighP95Latency`
- `AIGatewayCostSpike`

### SEV3

Minor issue.

Examples:

- dashboard panel broken
- non-critical alert
- dev/staging issue

Typical alerts:

- `AIPlatformPodRestarts` in dev or staging

## Incident process

1. Declare severity.
2. Assign incident lead.
3. Start timeline.
4. Triage dashboards/logs/traces.
5. Mitigate.
6. Communicate status.
7. Resolve.
8. Write postmortem.

## Initial triage checklist

- What changed recently?
- Is the API ready endpoint passing?
- Are pods healthy?
- Is database connectivity working?
- Is Redis connectivity working?
- Are errors provider-related or internal?
- Is one project/app causing the issue?
- Is one model route causing the issue?
- Is rollback safe?
- Is database restore required instead of rollback?

## Example demo incident

Scenario:

A deployment introduces a gateway error that causes 5xx responses.

Expected response:

1. `AIGatewayElevated5xxRate` fires.
2. Operator declares SEV1 if production users are broadly affected, otherwise SEV2.
3. Operator checks the Reliability dashboard for 5xx rate and gateway error category.
4. Operator searches Loki logs for 5xx records and opens a representative request ID.
5. Operator uses the request log trace ID to inspect the matching trace.
6. Operator confirms the issue started after the latest deploy.
7. Operator checks rollback safety in `docs/runbook.md`.
8. Operator triggers `.github/workflows/rollback.yml`.
9. Smoke tests pass and the alert resolves.
10. Incident doc is updated with timeline, root cause, mitigation, and follow-up.

If the incident includes durable data corruption, accidental deletion, or a failed destructive migration, stop the rollback-only flow and use `docs/backup-restore.md` for the database restore decision. Restoring RDS, changing production secrets, or redirecting production traffic requires explicit approval.

Rollback record:

- environment
- Helm release
- previous revision
- rollback target revision
- reason
- smoke test result
- follow-up owner
