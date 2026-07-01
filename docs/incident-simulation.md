# Incident Simulation

## Scenario

A new gateway release causes a spike in provider failures and HTTP 5xx responses.

## Signals

Expected alerts:

- `AIGatewayHighErrorRate`
- `AIGatewayElevated5xxRate`
- possibly `AIGatewayHighP95Latency`

Dashboard checks:

- Reliability dashboard: 5xx rate, gateway error rate, gateway p95 latency
- Logs dashboard: recent 5xx logs and request-correlated logs
- Cost dashboard: retry-related cost or token change

## Timeline

1. Alert fires for elevated 5xx rate.
2. Incident lead declares SEV1 for production or SEV2 for staging.
3. Operator opens the Reliability dashboard.
4. Operator checks whether failures correlate with a recent deploy.
5. Operator searches Loki for 5xx logs:

   ```logql
   {component="api"} | json | status_code >= 500
   ```

6. Operator selects a request ID and inspects related logs and trace spans.
7. Operator confirms failures started after the latest release.
8. Operator checks rollback safety:
   - no destructive migration
   - no secret rotation dependency
   - previous Helm revision is known-good
9. Operator triggers `.github/workflows/rollback.yml`.
10. Rollback waits for deployment rollout and smoke tests.
11. Operator verifies:
    - API readiness
    - web health
    - error rate recovery
    - p95 latency recovery
    - request logs continue to write
12. Incident timeline is updated with root cause, rollback revision, validation, and follow-ups.

## Demo Commands

Simulate provider failure locally:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"[simulate_failure] demo incident"}'
```

Simulate transient provider retry locally:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"[simulate_transient_failure] retry demo"}'
```

Generate small local load:

```bash
python scripts/smoke_load.py --requests 20 --concurrency 4
```

## Expected Follow-Ups

- Add a regression test if the incident was code-related.
- Add an alert or dashboard panel if detection lagged.
- Add a runbook note if triage was unclear.
- Adjust retry, timeout, or route defaults if provider behavior caused avoidable impact.
- Record any data recovery decision in `docs/backup-restore.md` terms.

## Boundaries

Do not run production rollback, change production traffic, mutate cloud resources, rotate secrets, or restore databases during a demo without explicit approval.
