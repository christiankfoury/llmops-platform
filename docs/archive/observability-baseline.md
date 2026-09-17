> Historical document. Current behavior and scope are described in the [documentation index](../README.md).

# Observability

Java migration status: Phase 57 now implements [Java metrics, safe structured logs and tracing](../java-observability.md), including a separate loopback management listener. The historical sections below describe the Python reference and existing dashboard assets. Docker/Helm cutover is Phase 58; the runnable monitoring stack, Alloy replacement, screenshots and alert evidence are Phase 62.

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

## External app telemetry

Phases 31-40 add the first connected external client app: Proofbase sends normalized LLM usage events into this platform before any provider calls are routed through the gateway.

Phases 41-47 add the second connected external client app: AgentOps sends normalized workflow and agent-step telemetry while keeping workflow execution, prompts, generated outputs, tools, and workflow state in AgentOps.

Phase 32 adds `POST /v1/usage/llm-events` for external telemetry ingestion. Accepted events are authenticated with application API keys, persisted as gateway request records with external event fields, optionally written to cost records, and included in the existing usage summary and request-list endpoints.

External events should include bounded operational fields such as source application, operation type, external request ID, model, prompt version, token counts, estimated cost, latency, status, and error category. They should not include API keys, provider credentials, full prompts, full questions, retrieved chunks, citations, document text, uploaded file contents, workflow input/output JSON, generated outputs, tool arguments, or tool results by default.

The external telemetry path must be best-effort for client apps. A telemetry outage should create local diagnostic logs, not break Proofbase user workflows or AgentOps workflow runs.

The Phase 31 contract lives in [external-telemetry-contract.md](../external-telemetry-contract.md). It defines the Proofbase operation taxonomy, required and optional fields, sensitive-data exclusions, idempotency strategy, and retry semantics that the Phase 32 ingestion API should implement.

The final Proofbase connection summary lives in [proofbase-integration.md](../proofbase-integration.md). It documents what is centralized and what remains in Proofbase.

The final AgentOps connection summary lives in [agentops-integration.md](../agentops-integration.md). It documents how AgentOps agent-step and workflow-summary telemetry appears centrally while AgentOps keeps workflow execution and payload ownership.

Phase 32 ingestion metrics include:

- `llm_external_telemetry_events_total`
- `llm_external_telemetry_errors_total`
- `llm_external_telemetry_estimated_cost_usd_total`
- `llm_external_telemetry_tokens_total`

Dashboard interpretation:

- `source_app=proofbase` isolates Proofbase traffic from gateway-originated traffic.
- `operation_type` distinguishes RAG query, streaming query, Markdown cleanup, query decomposition, and embedding generation events.
- `source_app=agentops` isolates AgentOps traffic from gateway-originated and Proofbase traffic.
- `operation_type=agent_step` identifies model-backed AgentOps step events that may include token and estimated-cost data.
- `operation_type=workflow_summary` identifies aggregate terminal workflow status events; these intentionally omit token and cost fields to avoid double-counting.
- `response_type=structured_json` on AgentOps metadata means the source app performed structured generation without sending the structured output.
- Estimated cost should be treated as operational cost visibility, not invoice-grade billing.
- `pricing_status=unpriced` or `unknown` means token/count visibility exists but cost should not be used for financial reporting.

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
