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

### High latency

Check:

- provider latency
- database query latency
- CPU/memory saturation
- pod count and HPA
- network issues

### Cost spike

Check:

- requests by project/app
- requests by model
- token usage
- recent route changes
- abusive API key usage

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

## Post-incident

1. Record timeline.
2. Record impact.
3. Record root cause.
4. Record detection gap.
5. Add test, alert, or runbook improvement.
