# Portfolio Demo Plan

## Goal

Show a recruiter or hiring manager that this is a serious production infrastructure project, not just a small AI app.

## 60-second pitch

I built a production-style LLMOps platform. Apps call a central LLM gateway instead of calling model providers directly. The gateway handles API keys, prompt versions, model routing, request logs, latency, failures, and estimated cost.

The main focus is infrastructure: Terraform-managed AWS infrastructure, Kubernetes on EKS, Helm releases, GitHub Actions CI/CD, staged deployments, rollback workflows, OpenTelemetry tracing, Prometheus metrics, Grafana dashboards, Loki logs, External Secrets, and reliability runbooks.

## Portfolio positioning

Pair this project with Proofbase when explaining the portfolio:

- Proofbase: a realistic permission-aware RAG product with citations, scoped retrieval, document workflows, and benchmarked answer quality.
- Production AI Platform: the production LLMOps layer that centralizes model access, cost, latency, errors, traces, secrets, deployments, rollback, and cloud operations.

The clean demo story: Proofbase shows what the AI product does; this project shows how AI workloads are operated responsibly in production. Proofbase is now presented as a telemetry-connected client app first, with gateway-routed provider calls as a later step once the gateway supports Proofbase's richer RAG call patterns.

## Demo flow

1. Show README architecture diagram.
2. Run local app with Docker Compose.
3. Send a gateway request.
4. Show request in dashboard.
5. Send the local Proofbase demo telemetry event and filter the dashboard to `source_app=proofbase`.
6. Show cost/latency/error metrics.
7. Show CI workflow.
8. Show Terraform modules.
9. Show Helm chart values for dev/staging/prod.
10. Show Grafana dashboard.
11. Show Loki logs by request ID.
12. Show rollback workflow.
13. Show incident runbook, including the external telemetry outage section.

## Screenshots to capture

- Dashboard overview
- Proofbase-filtered dashboard view
- Request table
- Cost dashboard
- Latency/error dashboard
- Grafana overview
- Loki request logs
- GitHub Actions CI
- GitHub Actions deploy
- Helm release
- Architecture diagram

## Final resume bullets

- Built a production-grade LLMOps platform with FastAPI, Next.js, PostgreSQL, Redis, and Kubernetes.
- Provisioned AWS infrastructure with Terraform, including EKS, ECR, RDS PostgreSQL, Redis, IAM, and secret references.
- Implemented Helm-based deployments across dev, staging, and prod with GitHub Actions CI/CD and rollback workflows.
- Added observability with OpenTelemetry traces, Prometheus metrics, Grafana dashboards, and Loki structured logs.
- Implemented API key auth, prompt versioning, model routing, request logging, latency tracking, error tracking, and estimated LLM cost monitoring.
- Documented incident response, backup/restore, security baseline, and cloud cost controls.
- Connected Proofbase as a telemetry-first client app for centralized LLM usage, latency, token, error, and estimated-cost visibility while preserving the RAG/product boundary.

## AgentOps handoff

AgentOps Workflow Platform is the next integration target. Its existing LLM client and cost-tracking models already expose model, token, cost, latency, status, retry, workflow, and agent-step data. The next sequence should reuse the external telemetry API foundation and add an agent/workflow operation taxonomy without redesigning ingestion.
