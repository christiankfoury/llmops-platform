# Observability

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

The repository does not create a collector in Phase 19. Later observability phases add Prometheus, Grafana, Loki, and collector manifests or Helm integration.

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
