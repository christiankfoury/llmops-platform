# Observability

## Implemented application signals

The Java runtime emits operational JSON logs, bounded metrics and OpenTelemetry spans.
Logs and traces carry request/trace identifiers and safe failure categories, without
prompt text, generated output, provider payloads or credentials. Telemetry integrations
accept metadata only. [Java instrumentation](java-observability.md)

Prometheus metrics use `/actuator/prometheus` on private management port **9080**.
This is not the old Python `/metrics` application-port endpoint. Readiness and liveness
remain application health endpoints. CI checks signal content and privacy behavior;
local Compose does not expose the management port to the host.

The web dashboard can show usage, cost, latency, errors and configuration through
project-authorized APIs. Its default synthetic mode is fixed data, separate from those
signals. [Screenshots and provenance](dashboard-screenshots.md)

## Monitoring stack status

Prometheus, Grafana, Loki, tracing and alerts produced dated local prototype evidence.
Final supported images, compatibility, delivery and monitoring CI remain incomplete
because of [deferred vulnerability findings](security/monitoring-vulnerability-backlog.md).
The preserved local monitoring work is not committed as a completed release.

[Prototype evidence](archive/phase-reviews/phase-62.md) records what ran and its limits.
Existing legacy Promtail assets are historical configuration. The local Alloy proposal
and custom rebuild experiments are not part of the eligible application delivery.
No screenshot in the current application gallery claims live Grafana or AWS evidence.

## Operational use

Use [incident response](incident-response.md), [the runbook](runbook.md) and
[local recovery commands](local-recovery-rehearsal.md) for scoped investigation.
The recovery rehearsal proves local behavior, not AWS availability, RTO/RPO or PITR.
Real alert delivery, monitoring installation and public/private access must be verified
within the separately approved AWS demonstration after the monitoring blocker clears.
