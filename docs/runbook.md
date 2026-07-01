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

## Post-incident

1. Record timeline.
2. Record impact.
3. Record root cause.
4. Record detection gap.
5. Add test, alert, or runbook improvement.
