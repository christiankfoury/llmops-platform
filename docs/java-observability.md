# Java metrics, logs and traces

Phase 57 implements the Java runtime's operational instrumentation. AWS remains the target. Runtime image/Helm cutover follows in Phase 58; the runnable monitoring stack and real dashboard/alert evidence follow in Phase 62. Existing Python monitoring instructions describe the reference runtime until cutover.

## Management access

The application listener serves business APIs and minimal `/health`, `/health/live` and `/health/ready` responses. Actuator uses a separate listener: `MANAGEMENT_BIND_ADDRESS=127.0.0.1`, `MANAGEMENT_PORT=9080` by default. Startup refuses a disabled or shared management port. Main-port `/actuator/**` routes return 404.

Only management `/actuator/prometheus` and health groups are exposed. Health details remain hidden; env, configprops, heapdump, mappings, shutdown, loggers, discovery and JMX are disabled. Management routes have no bearer login: access depends on the loopback/private listener and deployment network boundary. Never publish this port through public ingress, host-port mappings or load balancers. Phase 58 wires explicit monitoring access and network policy when the pod must bind beyond loopback. The tests check real separate listeners and a Redis outage through management readiness/liveness.

```sh
curl http://127.0.0.1:9080/actuator/prometheus
curl http://127.0.0.1:9080/actuator/health/readiness
```

## Metric contracts

Micrometer/Prometheus retains the names used by the existing overview, cost and reliability dashboards. HTTP metrics cover all /v1/ requests, including pre-authentication admission refusals. Gateway request/error metrics likewise count HTTP gateway attempts, including invalid keys and malformed payloads. Cost and token counters increment only after the request/cost transaction commits. Database rows remain the durable source; in-process counters reset on restart and are not invoice records.

| Metric family | Dimensions / meaning |
|---|---|
| `http_requests_total` | route, method, status_code |
| `http_request_duration_seconds_bucket` | Same dimensions; end-to-end API handling |
| `llm_gateway_requests_total` | provider, model, succeeded/failed HTTP status |
| `llm_gateway_errors_total` | provider, model, bounded error_category |
| `llm_gateway_request_duration_seconds_bucket` | provider, model; includes admission and response work |
| `llm_gateway_estimated_cost_usd_total` | provider, model; committed success only |
| `llm_gateway_tokens_total` | provider, model, input/output token_type |
| `llm_gateway_model_routing_total` | provider, model; resolved route selections, including later quota refusals |
| `llm_gateway_api_key_auth_failures_total` | bounded environment; gateway 401 responses |
| `llm_gateway_rate_limit_rejections_total` | bounded environment; gateway 429 responses |
| `platform_dependency_up` | postgresql/redis from the bounded readiness snapshot |
| `platform_ready` | Required dependencies, fresh snapshot and drain state |

The four `llm_external_telemetry_*` families retain their Phase 53 source/operation/result/error/token labels and accepted-only accounting; duplicate replays do not add cost/tokens. Gateway families do not double-count these external events.

Route labels are exactly gateway, telemetry, operator or other. Methods use the seven supported HTTP names or OTHER; status codes are bounded to 100-599. Gateway provider/model labels are mock/mock-llm-small or unknown; environment and error categories use finite vocabularies. No path/query, request/trace/project/application/key IDs, prompt/version names, user model strings or customer metadata become labels. Spring's separate automatic HTTP request meter is suppressed in favor of this explicit bounded contract. JVM/process/pool metrics remain available.

Latency histograms have explicit boundaries at 10/50/100/250/500 ms and 1/2/5/10/30 seconds. Tests send real traffic, scrape the actual endpoint, and check every application metric name referenced by the existing dashboard JSON. The log dashboard's queried fields remain compatible. Query execution, populated Grafana screenshots and fired/resolved alerts require the Phase 62 monitoring stack; a successful scrape is not that evidence.

## Structured logs

The console/file formatter emits one JSON record per log event. Operational records contain timestamp, lowercase level, component, logger, event, bounded request ID, trace/span IDs, fixed route/method, status and latency. Successful machine authentication adds trusted project/application UUIDs, including later configuration or telemetry errors. Resolved gateway configuration adds prompt version and provider/model; gateway execution and committed telemetry add their generated business request ID. A committed gateway success adds token counts and decimal cost. Errors add a finite category.

`request_id` is the bounded HTTP correlation ID; `gateway_request_id` is the persisted business ID. Use the latter to join an operational log with its PostgreSQL request row, then use `trace_id` to locate the sampled trace. A trace ID does not imply that a trace was exported. Callers must use non-sensitive correlation IDs. IDs are log fields, never Loki stream labels or Prometheus dimensions.

The formatter never exports formatted messages, argument arrays, arbitrary MDC, stack traces, exceptions, raw database/provider errors, URLs/queries, credentials, prompt text, generated output or request bodies. A strict key/value allowlist applies to operational records. Framework events retain timestamp, level and sanitized logger with `event=framework_event`; diagnostic messages are deliberately omitted, even on failure. This reduces diagnostic detail. Use safe error categories, dependency gauges and traces first; reproduce with synthetic inputs in an isolated environment if detailed debugging is necessary. Do not enable a raw logging formatter on a deployed service carrying real data.

## Trace lifecycle and export

Explicit OpenTelemetry SDK instrumentation creates `http.gateway` and fixed telemetry/operator/other server spans. Gateway children cover `gateway.authentication`, `gateway.prompt.lookup`, `gateway.model.routing`, `gateway.provider.call`, `gateway.database.write` and `http.response.write`. The response span covers message conversion/write through request-filter completion. Database recording spans encompass the transaction's commit. Provider work transfers OTel context to the bounded worker and closes it on completion/failure/cancellation; retries create separate provider-call spans. Telemetry adds validation and database-write spans using the same machine authentication stage.

Incoming W3C traceparent version 00 must have the exact bounded hexadecimal shape and nonzero valid identifiers. Invalid parents start a new trace. No baggage or tracestate is read. `X-Trace-ID` returns the current trace ID; IDs are correlation only and cannot authorize anything. Span attributes are fixed route/method/status fields. No SQL statements, exception events, headers, provider payloads or client content are recorded. No automatic Java agent or database instrumentation captures extra attributes.

`TRACE_SAMPLE_PROBABILITY` defaults to 0.1 and supports 0-1. Local trace-ID sampling ignores the remote sampled flag, so that flag alone cannot force collection. Sampling is not a security quota: clients can choose trace IDs, and admission limits/export queues supply separate bounds.

Trace export is disabled until `OTLP_TRACES_ENDPOINT` is explicitly set to the complete OTLP HTTP `/v1/traces` URL. HTTPS with normal certificate verification is required outside local/test; embedded URL credentials, queries and fragments are rejected. A local example is `http://127.0.0.1:4318/v1/traces`. No real collector or cloud credential is configured by this phase.

The SDK limits each span to 16 attributes of at most 128 characters and records no events/links. Export uses a 512-span queue, batches of 64, one-second scheduling and one-second connection/export timeouts. Collector failures occur on the bounded export worker and cannot delay provider work. Queue pressure, sampling, failure or shutdown may drop traces; traces are not durable audit records. Required tests exercise real OTLP HTTP delivery, exporter failure, parent/child relationships, worker context cleanup and error-path redaction.

References: [Spring Boot structured logging](https://docs.spring.io/spring-boot/reference/features/logging.html), [Spring Boot endpoint exposure](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html), [OpenTelemetry Java SDK](https://opentelemetry.io/docs/languages/java/sdk/).
