# Observability

## Prometheus metrics

Phase 20 adds a Prometheus-compatible `/metrics` endpoint to the API.

The endpoint exposes:

- `http_requests_total`
- `http_request_duration_seconds`
- `llm_gateway_requests_total`
- `llm_gateway_errors_total`
- `llm_gateway_request_duration_seconds`
- `llm_gateway_estimated_cost_usd_total`
- `llm_gateway_tokens_total`
- `llm_gateway_api_key_auth_failures_total`
- `llm_gateway_rate_limit_rejections_total`

Metrics use bounded labels such as HTTP method, route template, status code, provider, model, environment, gateway status, token type, and error category. They intentionally avoid request IDs, API key IDs, project IDs, prompt content, or trace IDs to prevent high-cardinality and sensitive metrics.

The Helm chart and raw Kubernetes API Service include Prometheus scrape annotations:

```yaml
prometheus.io/scrape: "true"
prometheus.io/path: /metrics
prometheus.io/port: "8000"
```

Local verification:

```bash
curl http://localhost:8000/metrics
```

`llm_gateway_rate_limit_rejections_total` increments when the gateway rejects a request with HTTP 429 after the configured API-key-hash rate limit is exceeded.

Prometheus server deployment is not installed by this repository, but scrape annotations and alert rule files are included for an approved monitoring stack to consume.

## Grafana dashboards

Phase 21 adds provisionable Grafana dashboard JSON for:

- Production AI Platform Overview
- Production AI Platform Reliability
- Production AI Platform Cost
- Production AI Platform Logs

Dashboard files live in `infra/monitoring/grafana/dashboards`, with provisioning config in `infra/monitoring/grafana/provisioning/dashboards`.

The dashboards map directly to the Phase 20 metrics and use a Prometheus datasource variable named `datasource`. See `infra/monitoring/grafana/README.md` for provisioning paths and `docs/dashboard-screenshots.md` for the screenshot capture checklist.

The repository provides dashboard, datasource, Promtail, and alert-rule assets. It does not install a live Grafana, Prometheus, Loki, or Alertmanager stack by default.

## Loki structured logging

Phase 22 adds Loki integration assets for the API's structured JSON logs.

The API already emits JSON request logs with:

- `request_id`
- `trace_id`
- `level`
- `logger`
- `message`
- `http_method`
- `http_path`
- `status_code`
- `latency_ms`
- `error_category` when present

Promtail config lives in `infra/monitoring/loki/promtail-config.yaml`. It labels bounded fields such as namespace, pod, component, app, level, logger, status code, and error category. Request IDs and trace IDs remain JSON fields so they are searchable without becoming high-cardinality Loki labels.

Useful LogQL examples:

```logql
{component="api"} | json | request_id="http_abc123"
{component="api"} | json | trace_id="0123456789abcdef0123456789abcdef"
{component="api"} | json | status_code >= 500
```

See `infra/monitoring/loki/README.md` for more queries and label guidance.

## Alerts

Phase 23 adds Prometheus alert rules and an Alertmanager placeholder config.

Alert files live in:

- `infra/monitoring/prometheus/rules/ai-platform-alerts.yaml`
- `infra/monitoring/alertmanager/alertmanager.yaml`

Rules cover:

- high gateway error rate
- high gateway p95 latency
- elevated HTTP 5xx rate
- pod restarts
- PostgreSQL connectivity failure through `pg_up`
- estimated LLM cost spike

The Alertmanager config uses a `.invalid` webhook placeholder and must be replaced with an approved receiver before any live deployment.

## OpenTelemetry tracing

Phase 19 adds API tracing with OpenTelemetry.

Tracing is disabled by default and can be enabled per environment:

```bash
OTEL_TRACING_ENABLED=true
OTEL_SERVICE_NAME=production-ai-platform-api-dev
OTEL_TRACES_EXPORTER=console
```

For collector-based environments, use the OTLP HTTP exporter:

```bash
OTEL_TRACING_ENABLED=true
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4318/v1/traces
```

The Helm chart exposes the same settings under `api.config`.

Current spans:

- `api.request`
- `gateway.request`
- `gateway.auth`
- `gateway.prompt_lookup`
- `gateway.model_routing`
- `gateway.provider_call`
- `gateway.database_write`
- `gateway.response_serialization`

Trace attributes include:

- request ID
- project ID
- application ID and slug
- prompt name and version
- provider and model
- token counts
- estimated cost
- status and error category when available

The API propagates `X-Request-ID` from incoming requests or creates one when the header is missing. Responses include `X-Request-ID`, and request logs include both `request_id` and `trace_id` fields when a valid trace context exists.

## Collector integration

The repository does not create an OpenTelemetry Collector by default. Grafana, Loki, and alerting assets are included, while live collector installation remains an environment-specific deployment decision.

Expected collector shape:

```text
API -> OTLP HTTP exporter -> OpenTelemetry Collector -> tracing backend
```

The collector should receive OTLP HTTP traces on port `4318` and export to the chosen backend. Keep provider credentials in Kubernetes secrets or cloud secret management rather than ConfigMaps.

## Local verification

Run the API locally with console tracing:

```bash
OTEL_TRACING_ENABLED=true OTEL_TRACES_EXPORTER=console uvicorn app.main:app --reload
```

Send a request:

```bash
curl -H "X-Request-ID: local-trace-demo" http://localhost:8000/health
```

The response should include `X-Request-ID: local-trace-demo`. Console output should include spans when tracing is enabled.
