# Prometheus Alert Rules

Phase 23 adds alert rule files for the Production AI Platform.

## Files

- `rules/ai-platform-alerts.yaml`: Prometheus alert rules.
- `../alertmanager/alertmanager.yaml`: placeholder Alertmanager routing config.

## Rule Coverage

Gateway alerts use metrics emitted by the API:

- `llm_gateway_errors_total`
- `llm_gateway_requests_total`
- `llm_gateway_request_duration_seconds_bucket`
- `http_requests_total`
- `llm_gateway_estimated_cost_usd_total`

Infrastructure alerts use common exporter metrics expected from a production monitoring stack:

- `kube_pod_container_status_restarts_total` from kube-state-metrics.
- `pg_up` from postgres-exporter or an equivalent RDS/PostgreSQL exporter.

## Alertmanager Placeholder

The Alertmanager config uses a `.invalid` webhook URL by design. Replace it with an approved receiver such as PagerDuty, Slack, email, or an internal webhook only after the destination and secret handling are approved.

Do not commit real routing secrets, webhook tokens, or notification credentials.
