# Contributing

Start with [local setup](docs/deployment.md), [architecture](docs/architecture.md) and
[testing](docs/testing.md). Java in `apps/api-java` is the default runtime;
`apps/api` remains a Python compatibility reference. Flyway is the sole migration owner.

## Changes

Create a focused branch and pull request. Describe the problem, resulting behavior,
validation and relevant tradeoffs. Use conventional commits. Required CI must pass
on the current PR revision before merging; the merged main revision receives its
own complete CI and immutable release verification. A second reviewer is not required
for this solo project, but checks and branch protections must not be bypassed.

Use synthetic data and local placeholders. Never commit environment files, secrets,
state, database dumps or customer content. Add tests for meaningful failure modes;
do not replace database integration tests with skipped or mocked success claims.
Application code, documentation and static infrastructure checks should remain scoped.

## Project boundaries

This platform handles the gateway and operational telemetry. Proofbase owns RAG;
AgentOps owns workflow execution. Their content and provider payloads stay with them.
AWS deployment, public services, real DNS/TLS, secret rotation and destructive cleanup
require explicit approval. Monitoring remediation remains deferred; do not add scanner
exceptions or adopt unreviewed prototype images to make checks pass.

Preserve the [MIT license](LICENSE) and applicable third-party notices.
Report vulnerabilities through [the security policy](SECURITY.md).
Maintainer execution and spending rules are in [AGENTS.md](AGENTS.md).
