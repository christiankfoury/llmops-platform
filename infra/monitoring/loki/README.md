# Loki Logging Integration

Phase 22 adds Loki and Promtail integration assets for the API's structured JSON logs.

This phase does not deploy Loki. It provides the config shape needed by a later monitoring stack phase.

## Files

- `promtail-config.yaml`: Kubernetes pod log scrape config for Production AI Platform workloads.
- `../grafana/provisioning/datasources/loki.yaml`: Grafana Loki datasource provisioning.
- `../grafana/dashboards/ai-platform-logs.json`: Grafana logs dashboard with error and request-correlation panels.

## Label Strategy

Promtail labels only bounded fields:

- `namespace`
- `pod`
- `container`
- `component`
- `app`
- `level`
- `logger`
- `status_code`
- `error_category`

High-cardinality fields remain searchable JSON fields instead of labels:

- `request_id`
- `trace_id`
- `latency_ms`
- `http_path`

This keeps Loki indexes small while preserving request and trace correlation.

## LogQL Examples

Find one request by request ID:

```logql
{component="api"} | json | request_id="http_abc123"
```

Find logs for one trace:

```logql
{component="api"} | json | trace_id="0123456789abcdef0123456789abcdef"
```

Show recent API server errors:

```logql
{component="api"} | json | status_code >= 500
```

Error log rate:

```logql
sum(rate({component="api"} | json | status_code >= 500 [5m]))
```

Log-derived p95 latency:

```logql
quantile_over_time(0.95, {component="api"} | json | unwrap latency_ms [5m])
```

## Sensitive Data

The API request log format intentionally avoids API key values, provider credentials, raw prompts, database URLs, Redis URLs, and other secrets. Keep that rule when adding new log fields.
