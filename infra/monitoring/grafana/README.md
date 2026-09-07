# Grafana Dashboards

Phase 21 adds provisionable Grafana dashboards for the metrics emitted by the API in Phase 20.

## Dashboards

- `dashboards/ai-platform-overview.json`
- `dashboards/ai-platform-reliability.json`
- `dashboards/ai-platform-cost.json`
- `dashboards/ai-platform-logs.json`

The dashboards use a Grafana datasource variable named `datasource`. Select the Prometheus datasource when importing manually, or provision a datasource with UID `prometheus`.

The logs dashboard uses a Loki datasource variable named `loki`. The sample datasource provisioning file in `provisioning/datasources/loki.yaml` creates a datasource with UID `loki`.

## Provisioning

The provisioning config in `provisioning/dashboards/ai-platform.yaml` expects dashboard JSON files at:

```text
/var/lib/grafana/dashboards/production-ai-platform
```

Typical container mounts:

```text
infra/monitoring/grafana/provisioning/dashboards -> /etc/grafana/provisioning/dashboards
infra/monitoring/grafana/provisioning/datasources -> /etc/grafana/provisioning/datasources
infra/monitoring/grafana/dashboards -> /var/lib/grafana/dashboards/production-ai-platform
```

This repository does not deploy Grafana or Prometheus by default. These files are provisionable assets for an approved monitoring stack.

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

The logs dashboard maps to structured JSON log fields emitted by the API:

- `request_id`
- `trace_id`
- `level`
- `logger`
- `http_method`
- `http_path`
- `status_code`
- `latency_ms`
- `error_category`

## Java metric compatibility (Phase 57)

The Java HTTP integration test emits real traffic and verifies every application metric name referenced by the overview, cost and reliability dashboards against `/actuator/prometheus` on its private management listener. Provider/model/error/status dimensions and histogram buckets remain compatible. Java logs retain the fields queried by the log dashboard; `method` and the fixed `route` replace the older informational `http_method`/raw `http_path` fields. These IDs remain fields, not stream labels. See [Java observability](../../../docs/java-observability.md). This is contract evidence; running dashboards and alerts follow in Phase 62.
