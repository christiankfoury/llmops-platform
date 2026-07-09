# Demo Script

## Goal

Show in 10 to 15 minutes that this is a production AI platform, not only an LLM API wrapper.

## Opening Pitch

I built a lightweight LLM gateway and dashboard, then wrapped it in the kind of infrastructure and operations work expected from a production platform: Terraform, Kubernetes, Helm, CI/CD, observability, secrets, rollback, backups, cost controls, security hardening, and runbooks.

## Walkthrough

1. README
   - Show the 60-second summary.
   - Explain the portfolio relationship: Proofbase is the RAG product layer, AgentOps is the workflow/orchestration layer, and this repo is the operating layer.

2. Local app
   - Run `docker compose up --build`.
   - Run `make api-migrate` and `make api-seed`.
   - Open `http://localhost:3000`.

3. Gateway request
   - Send the local curl request from the README.
   - Point out request ID, provider/model, latency, token estimate, and estimated cost.

4. Dashboard
   - Show usage totals, errors, average latency, estimated cost, recent requests, prompt versions, and model routes.
   - Mention that this is real API-backed data, not static marketing UI.

5. Proofbase telemetry demo
   - Run `python scripts/send_proofbase_browser_demo_event.py`.
   - Open the dashboard, filter **Source App** to `proofbase`, and show the `Proofbase / Enterprise Knowledge Agent` request.
   - Explain that Proofbase remains the RAG product layer while this platform centralizes usage, cost, latency, and failure visibility.
   - Use [proofbase-browser-telemetry-demo.md](proofbase-browser-telemetry-demo.md) for the browser checklist and screenshot rules.

6. AgentOps telemetry demo
   - Run `python scripts/send_agentops_browser_demo_event.py`.
   - Open the dashboard, filter **Source App** to `agentops`, and show the `AgentOps Workflow Platform / AgentOps Workflow Platform` request.
   - Explain that AgentOps remains the workflow/orchestration layer while this platform centralizes safe agent-step and workflow-summary telemetry.
   - Use [agentops-browser-telemetry-demo.md](agentops-browser-telemetry-demo.md) for the browser checklist and screenshot rules.

7. Backend depth
   - Show SQLAlchemy models, Alembic migration, gateway service, pricing service, rate limiter, metrics, and tracing.

8. Infrastructure
   - Show Terraform environment roots and reusable modules.
   - Show EKS, ECR, RDS, Redis, Secrets Manager, IAM, and optional budget modules.
   - Emphasize that applying Terraform is intentionally approval-gated.

9. Kubernetes and Helm
   - Show raw manifests.
   - Show the Helm chart and dev/staging/prod values.
   - Explain probes, resources, security contexts, NetworkPolicies, HPA, and PDB.

10. CI/CD
   - Show `.github/workflows/ci.yml`.
   - Show deploy-dev, deploy-staging, deploy-prod, and rollback workflows.
   - Explain immutable image tags, scans, environment approvals, and smoke tests.

11. Observability
   - Show `docs/observability.md`.
   - Show Grafana dashboard JSON and Prometheus alert rules.
   - Explain request IDs, trace IDs, metrics, logs, and dashboard panels.

12. Reliability and incident response
    - Show `docs/runbook.md`.
    - Walk through `docs/incident-simulation.md`.
    - Show rollback workflow and backup/restore docs.

13. Cost and security
    - Show `docs/cost-analysis.md`.
    - Show `docs/security-baseline.md`.
    - Explain rate limits, hashed API keys, External Secrets, private data services, and optional AWS Budget alerts.

14. GitOps
    - Show Argo CD Application manifests.
    - Explain that GitHub Actions remains default, while Argo CD is an optional deployment control plane.

## Closing

The intentionally small app makes the platform work easy to inspect. The value is the production operating system around AI calls: deployment, monitoring, rollback, security, cost, and reliability.

## Resume Bullets

- Built a production-style LLMOps platform with FastAPI, Next.js, PostgreSQL, Redis, Docker, and Kubernetes.
- Defined AWS infrastructure with Terraform modules for EKS, ECR, RDS PostgreSQL, ElastiCache Redis, IAM, Secrets Manager, and budget alerts.
- Packaged releases with Helm and automated CI/CD through GitHub Actions with staged promotion and rollback workflows.
- Added OpenTelemetry traces, Prometheus metrics, Grafana dashboards, Loki log assets, and alert/runbook coverage.
- Implemented API key auth, prompt versioning, model routing, request logging, latency tracking, error tracking, rate limiting, and estimated LLM cost monitoring.
- Connected Proofbase and AgentOps as telemetry-first client apps while preserving their RAG and workflow product boundaries.
- Documented backup/restore, incident response, security baseline, GitOps, cost controls, and known limitations.
