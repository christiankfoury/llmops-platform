# Grafana Dashboards

Phase 21 adds provisionable Grafana dashboards for the metrics emitted by the API in Phase 20.

## Dashboards

- `dashboards/ai-platform-overview.json`
- `dashboards/ai-platform-reliability.json`
- `dashboards/ai-platform-cost.json`

The dashboards use a Grafana datasource variable named `datasource`. Select the Prometheus datasource when importing manually, or provision a datasource with UID `prometheus`.

## Provisioning

The provisioning config in `provisioning/dashboards/ai-platform.yaml` expects dashboard JSON files at:

```text
/var/lib/grafana/dashboards/production-ai-platform
```

Typical container mounts:

```text
infra/monitoring/grafana/provisioning/dashboards -> /etc/grafana/provisioning/dashboards
infra/monitoring/grafana/dashboards -> /var/lib/grafana/dashboards/production-ai-platform
```

This phase does not deploy Grafana or Prometheus. Later phases can package those pieces through Helm or a monitoring stack.

## Metric Coverage

The panels map to these Phase 20 metrics:

- `http_requests_total`
- `http_request_duration_seconds`
- `llm_gateway_requests_total`
- `llm_gateway_errors_total`
- `llm_gateway_request_duration_seconds`
- `llm_gateway_estimated_cost_usd_total`
- `llm_gateway_tokens_total`
- `llm_gateway_api_key_auth_failures_total`
- `llm_gateway_rate_limit_rejections_total`

Dashboard queries intentionally avoid request IDs, trace IDs, API key IDs, prompt content, and project IDs.
