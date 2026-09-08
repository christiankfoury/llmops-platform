# Five-minute local portfolio demo

Use a clean checkout and synthetic data. This script demonstrates current local
and CI evidence; AWS is not installed and Phase 62 monitoring is still blocked.
It authorizes no deployment, paid provider, secret, DNS/TLS or publication action.

1. **0:00 — Operations scope.** Show the README. Explain that Java provides a small
   gateway while Terraform, Kubernetes, releases, security and recovery are the
   main project. Proofbase owns RAG; AgentOps owns workflows; both send only safe
   operational telemetry to this platform.
2. **0:45 — Local request.** Use the README's Compose and mock request commands.
   Show the response's request ID, model, tokens and estimated cost. Java persists
   request/cost records. The current gateway has no paid-provider adapter.
3. **1:30 — Dashboard.** Open the default dashboard, or the [two captured views](assets/screenshots/phase-64.md).
   Point to “Synthetic demo · Fixed example data · Read only.” Open the synthetic
   request details. These fixtures do not change when a gateway/telemetry request
   arrives. Viewing real platform data requires OIDC sign-in and project grants;
   do not suggest these screenshots show the database or connected clients.
4. **2:15 — Trust and delivery.** Show successful current CI: Java integration
   tests with PostgreSQL/Redis, frontend/Python checks, full-history secrets,
   dependency/image scans and OCI digest-preserving promotion. Show separate
   publisher/migration/app identities and the held manual release workflow.
5. **3:15 — Recovery.** Show [Phase 63 evidence](phase-reviews/phase-63.md): 20/20
   requests, a Redis outage/recovery, graceful restart, compatible image rollback,
   and 24 request/cost records restored into a new database. Explain the small
   local sample and identical application-source rollback limitation.
6. **4:15 — Honest cloud boundary.** Show Terraform dev and Helm configuration,
   then [the monitoring backlog](security/monitoring-vulnerability-backlog.md).
   Metrics/logs/traces and alerts ran in a dated prototype; its final images and
   delivery are not eligible. One AWS dev/demo is planned after setup and approval.
   Staging/prod are optional static designs. Budgets notify; they are not caps.

Close with: “The capability I can demonstrate today is a tested local Java
operations platform with reproducible delivery and recovery evidence. The remaining
work is the monitoring release gate and one approved AWS demonstration.”

Do not run another load campaign or recreate monitoring just for this walkthrough.
Use existing evidence. No customer data, real tokens or unredacted terminal output
belongs in a screenshot or presentation.
