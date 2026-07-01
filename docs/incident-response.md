# Incident Response

## Severity levels

### SEV1

Critical production outage.

Examples:

- gateway unavailable
- widespread 5xx
- database unavailable
- secrets exposed

### SEV2

Major degradation.

Examples:

- high latency
- elevated error rate
- failed deploy with partial impact
- cost spike

### SEV3

Minor issue.

Examples:

- dashboard panel broken
- non-critical alert
- dev/staging issue

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

## Example demo incident

Scenario:

A deployment introduces a gateway error that causes 5xx responses.

Expected response:

1. Alert fires for high 5xx rate.
2. Operator checks Grafana dashboard.
3. Operator searches Loki logs by request ID.
4. Operator confirms issue started after latest deploy.
5. Operator triggers rollback workflow.
6. Smoke test passes.
7. Incident doc is updated.

Rollback record:

- environment
- Helm release
- previous revision
- rollback target revision
- reason
- smoke test result
- follow-up owner
