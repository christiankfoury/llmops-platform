# Project specification

Production AI Platform provides a Java LLM gateway, operational telemetry API and
Next.js usage dashboard. The focus is reproducible delivery, authorization,
infrastructure, recovery and cost visibility around a small application workload.

## Current implementation

- Java 21/Spring Boot MVC, PostgreSQL, Flyway migrations and Redis rate limits.
- Hashed application keys; versioned prompts and model routes; request, latency,
  failure and estimated-cost records. The gateway implements a mock provider only.
- OIDC operator authentication with project-scoped viewer/operator grants; the web
  session and proxy keep access tokens off browser-readable responses.
- Metadata-only telemetry integrations for Proofbase and AgentOps. They retain
  their own provider calls, content and orchestration.
- A read-only synthetic dashboard for local inspection without credentials.
  It is isolated from API/database traffic; authenticated mode displays real usage.
- CI builds and tests Java, Python reference and frontend code, checks dependencies,
  images, secrets and infrastructure, and verifies immutable OCI promotion.
- Terraform/Helm define AWS deployment and release boundaries. AWS is not deployed.

## Evidence and remaining work

The [local recovery rehearsal](docs/archive/phase-reviews/phase-63.md) covers a small
load sample, Redis outage/recovery, restart, compatible rollback and restoration into
a separate PostgreSQL target. These measurements are not cloud capacity or SLA claims.
Monitoring has dated prototype evidence; its final image/security/compatibility gate
remains [blocked](docs/security/monitoring-vulnerability-backlog.md).

Source publication is being prepared independently of AWS. A later cloud milestone
is one explicitly approved dev/demo environment. Separate staging/production
configurations are optional static designs, not deployed environments.
See [progress](phases-progress.md) and the [AWS checklist](docs/aws-launch-checklist.md).

## Boundaries

Proofbase owns RAG, retrieval and answer quality. AgentOps owns workflow/agent
execution. This platform owns the gateway, safe operational telemetry and infrastructure.
Do not add advanced RAG, workflow orchestration or paid provider integrations as part
of publication cleanup. Do not imply production use, HA, live cloud recovery or a
completed monitoring release. Preserve the MIT license and third-party notices.

Historical specifications and decisions are retained in the [archive](docs/archive/README.md).
