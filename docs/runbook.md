# Runbook

## Purpose

This runbook documents common operational tasks for the Production AI Platform.

## Check platform health

1. Check API readiness endpoint.
2. Check web dashboard.
3. Check Kubernetes pod status.
4. Check recent error logs.
5. Check Prometheus metrics.
6. Check Grafana dashboard.

## Common symptoms

### API pods crash looping

Check:

- recent deployment
- environment variables
- secret references
- database connectivity
- container logs
- image tag

### High error rate

Check:

- provider failures
- API key auth failures
- database latency
- Redis availability
- recent deploys
- rate limit events

Alert:

- `AIGatewayHighErrorRate`
- `AIGatewayElevated5xxRate`

Triage:

1. Open the Production AI Platform Reliability dashboard.
2. Check whether errors are HTTP 5xx, provider errors, auth failures, or config errors.
3. Search Loki for recent 5xx logs:

   ```logql
   {component="api"} | json | status_code >= 500
   ```

4. Pick a representative request ID and inspect correlated logs and traces.
5. Check recent deploys and model route changes.
6. Roll back if the error started after a release and the previous revision is known-good.

### High latency

Check:

- provider latency
- database query latency
- CPU/memory saturation
- pod count and HPA
- network issues

Alert:

- `AIGatewayHighP95Latency`

Triage:

1. Open the Reliability dashboard and compare HTTP p95 with gateway p95.
2. Check whether latency is isolated to one provider/model.
3. Review pod CPU and memory saturation.
4. Search logs for slow requests by latency:

   ```logql
   {component="api"} | json | latency_ms > 2000
   ```

5. Mitigate by scaling, routing to a safer model route, or rolling back a problematic deploy.

If HPA is not scaling as expected, check:

- `kubectl describe hpa`
- metrics-server availability
- CPU requests on the target Deployment
- current pod CPU utilization in Grafana or Kubernetes metrics
- PDBs blocking voluntary disruption during node maintenance

Provider retry behavior:

- The API uses `PROVIDER_MAX_ATTEMPTS`, `PROVIDER_RETRY_BACKOFF_MS`, and `PROVIDER_TIMEOUT_SECONDS` to bound provider retries.
- Repeated provider failures are still recorded as failed gateway requests and surfaced in metrics/logs.
- Do not raise retry attempts during a provider outage without checking cost and latency impact.

### Cost spike

Check:

- requests by project/app
- requests by model
- token usage
- recent route changes
- abusive API key usage

Alert:

- `AIGatewayCostSpike`

Triage:

1. Open the Cost dashboard.
2. Identify the provider/model driving the spike.
3. Compare token usage with request volume.
4. Check recent prompt or model route changes.
5. Disable or rotate an abusive key only with approval if it affects real users.
6. Roll back only if the spike was caused by a recent deploy or config change.

### External telemetry ingestion outage

Symptoms:

- Proofbase traffic disappears from the dashboard.
- AgentOps traffic disappears from the dashboard.
- `POST /v1/usage/llm-events` returns 401, 422, 409, or 5xx.
- External telemetry error metrics increase.
- Proofbase local logs report telemetry send failures.
- AgentOps local logs report telemetry send failures.

Triage:

1. Confirm the API health and readiness endpoints.
2. Check API logs for `/v1/usage/llm-events` status codes.
3. Separate auth failures from validation failures, duplicate conflicts, database failures, and platform 5xx errors.
4. Confirm the client telemetry endpoint points to the correct platform API:
   - Proofbase: `PROOFBASE_TELEMETRY_ENDPOINT`
   - AgentOps: `AGENTOPS_TELEMETRY_ENDPOINT`
5. Confirm the client app is using an active application API key, without printing the key value.
6. For 422 validation failures, compare the payload shape with `docs/external-telemetry-contract.md` and check for disallowed metadata keys.
7. For 409 duplicate conflicts, confirm the client is not reusing an event id for a changed payload.
8. For platform 5xx errors, inspect database connectivity and recent deploys before rolling back.
9. For AgentOps `workflow_summary` events, confirm missing token/cost fields are expected and are not treated as ingestion failure.

Reliability expectation:

- Do not block Proofbase user workflows because central telemetry is unavailable.
- Do not block AgentOps workflow runs because central telemetry is unavailable.
- Keep telemetry submission best-effort with short timeouts and local diagnostics.
- Backfill only sanitized operational events if a future client implements an approved replay path.

### Database connectivity failure

Check:

- RDS health and connectivity.
- Security groups and subnet routing.
- Database credentials and External Secrets sync.
- Application pod logs and readiness.
- Recent Terraform, secret, or deployment changes.

Alert:

- `AIPlatformDatabaseUnavailable`

Triage:

1. Confirm `pg_up` from the PostgreSQL exporter is `0`.
2. Check API readiness and recent API 5xx logs.
3. Inspect RDS status, maintenance events, and security group changes.
4. Verify the runtime database secret exists in the affected namespace.
5. Escalate to infrastructure owner before making cloud changes.

### Database restore

Use `docs/backup-restore.md` when data corruption, accidental deletion, a failed migration, or RDS infrastructure failure requires recovery.

Restore decision checks:

- Is rollback enough, or is durable data recovery required?
- What is the last known-good recovery point?
- Is the incident in dev, staging, or prod?
- Has risky write traffic been frozen?
- Will the restored database require secret or endpoint changes?
- Are destructive migrations involved?

Restore guardrails:

- Restore into a new RDS instance first.
- Keep the source database and snapshots until validation is complete.
- Do not print database URLs, passwords, dumps, or secret values in logs.
- Treat production secret updates, endpoint changes, and traffic shifts as explicit approval gates.

### Pod restarts

Alert:

- `AIPlatformPodRestarts`

Triage:

1. Inspect the restarted pod logs.
2. Check `kubectl describe pod` events.
3. Confirm whether restarts follow a deploy, secret change, or resource limit.
4. Roll back if the restart loop started after a release and smoke tests fail.

## Rollback decision

Rollback when:

- new deployment causes high 5xx rate
- readiness failures appear after deploy
- user-facing gateway path is broken
- cost spike is caused by config/deploy error
- fix is not immediately safe

Hotfix instead when:

- issue is isolated and fix is low-risk
- rollback would cause data/schema incompatibility
- feature flag/config change can safely mitigate

## Rollback workflow

Use `.github/workflows/rollback.yml` when a Helm release rollback is the safest mitigation.

Inputs:

- environment: `dev`, `staging`, or `prod`
- revision: Helm release revision to restore
- reason: incident or release reason
- confirmation:
  - `rollback` for dev or staging
  - `rollback-prod` for prod

Before triggering rollback:

1. Confirm the current incident symptom.
2. Inspect recent deployment or configuration changes.
3. Check Helm history for the target environment.
4. Select a known-good revision.
5. Confirm rollback will not conflict with database migrations, secret changes, or external dependency changes.

After triggering rollback:

1. Confirm workflow approval if production.
2. Watch Helm rollback output.
3. Confirm API and web rollout checks pass.
4. Confirm API readiness smoke test passes.
5. Confirm web dashboard smoke test passes.
6. Check recent error rate and latency.
7. Update the incident timeline with the rollback revision and result.

Manual equivalent:

```bash
aws eks update-kubeconfig --region us-east-1 --name production-ai-platform-prod-eks
helm history ai-platform-prod --namespace ai-platform-prod
helm rollback ai-platform-prod <revision> --namespace ai-platform-prod --wait --timeout 20m
kubectl rollout status deployment/ai-platform-prod-api --namespace ai-platform-prod --timeout=20m
kubectl rollout status deployment/ai-platform-prod-web --namespace ai-platform-prod --timeout=20m
curl --fail https://api.ai-platform.example.com/health/ready
curl --fail https://ai-platform.example.com
```

Rollback risks:

- A rollback can reintroduce an older application bug.
- A rollback may not be safe after destructive database migrations.
- A rollback may fail if required image tags were deleted from ECR.
- A rollback may not fix incidents caused by secrets, infrastructure, data services, DNS, TLS, or external provider outages.
- A rollback is not a database restore. Use `docs/backup-restore.md` if durable data corruption or data loss is part of the incident.

## Post-incident

1. Record timeline.
2. Record impact.
3. Record root cause.
4. Record detection gap.
5. Add test, alert, or runbook improvement.

## Java admission and readiness

For Java 429/503 responses, Redis/database recovery and shutdown, follow [Java reliability](java-reliability.md). Readiness refuses missing/stale dependencies; liveness stays healthy during a dependency outage. Inspect Retry-After and recover the dependency before changing quotas or restarting instances. All replicas must share identical namespace and limit settings. Never flush a shared Redis cache.
