# Contributing

Keep this repository focused on the AI operations layer. Proofbase owns RAG and
AgentOps owns workflows; do not move their prompts, outputs or tool payloads here.
Read [AGENTS.md](AGENTS.md), the spec and current phase before changing scope.

Use an isolated checkout when the main workspace contains unrelated work. The
current Java runtime lives in `apps/api-java`; `apps/api` is the Python contract
reference. Flyway is the sole migration owner after cutover. Never enable automatic
destructive schema updates or run two migration owners.

Use synthetic data and committed placeholder examples. Keep real `.env`, dumps,
state, credentials, tokens and local build evidence out of Git. Add focused tests
for meaningful behavior changes, run relevant checks from [testing](docs/testing.md),
and retain every mandatory CI gate, including actual PostgreSQL/Redis tests.
Use conventional commits and separate commits for actionable review findings.

Local code, tests, Docker builds and static infrastructure checks are normal work.
AWS apply/destroy/resources, data deletion, real secrets, production, DNS/TLS and
public exposure retain explicit approval gates. Do not bypass branch protection,
force-push main, lower scanner thresholds or activate exceptions.

The repository remains private and the license is undecided. Do not add a license,
change visibility or publish releases without the owner's separate decision.
Report security concerns through the process in [SECURITY.md](SECURITY.md).
