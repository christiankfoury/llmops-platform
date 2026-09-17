# Local platform and client integrations

Start the current Java/Next.js stack with [the local setup guide](deployment.md).
Use its synthetic dashboard without connecting another repository or a paid provider.

For an API-backed client demonstration, configure operator OIDC and project grants,
then follow the [Proofbase](proofbase-browser-telemetry-demo.md) or
[AgentOps](agentops-browser-telemetry-demo.md) telemetry guide. Their senders use
invented operational data; they do not run real RAG or agent workflows.

Actual client applications remain independently configurable. Their content, provider
credentials and execution stay outside this repository. Telemetry is best-effort and
must not break client work. See the integration contracts in the [documentation index](README.md).

The [earlier multi-repository setup](archive/local-portfolio-stack-baseline.md) records
historical Python development. It is not the current Java startup procedure.
