# Security baseline

## Application boundaries

Java is the default runtime. Machine keys are hashed, scoped and revocable; operator
access uses OIDC issuer/audience/signature validation and explicit project grants.
Unconfigured operator APIs fail closed. The Next.js proxy retains session, origin,
CSRF, request-size and upstream-response boundaries. [Operator design](java-operator-security.md)

Flyway is the only active migration owner. Application startup validates schema
rather than creating or changing it. Redis provides atomic distributed admission
limits. [Migration ownership](database-migration-handover.md) · [Reliability](java-reliability.md)

Synthetic mode serves fixed fixtures, rejects writes and has no backend/provider
connection. Logs, metrics and traces omit credentials, prompts and generated content.
Keep customer documents and tool payloads outside telemetry and screenshots.

## Delivery and infrastructure

- Full-history secrets, dependency/image scans, real integration tests and
  infrastructure checks remain mandatory. No scanner exception is active.
- PR jobs have read-only credentials. Only trusted-main image publication receives
  package-write permission. Private GHCR images retain explicit repository Actions access.
- Main requires PRs and current CI. Merged-main exact-revision evidence remains a
  separate release requirement; neither PR success nor cached results authorize deployment.
- Terraform owns load balancers; bootstrap owns TargetGroupBindings. The controller
  cannot write Ingress or manage AWS load balancers. Publisher, migration and
  application identities remain separate. [Ownership](targetgroupbinding-design.md)
- Local ports bind to loopback; management metrics are private. Workload configuration
  includes non-root execution, resource bounds, probes and referenced secrets.

## Current limits

AWS is not deployed. Live identity, network controls, secret synchronization and
monitoring require the approved launch checks. The [monitoring backlog](security/monitoring-vulnerability-backlog.md)
blocks monitoring/cloud deployment; publishing source does not accept that risk.
Historical reviews remain dated evidence, not security certification.

[Security reporting](../SECURITY.md) · [Publication record](publication-decisions.md) ·
[Historical baseline](archive/security-baseline-history.md)
