# Portfolio Demo Plan

## Goal

Show a recruiter or hiring manager that this is a serious production infrastructure project, not just a small AI app.

## 60-second pitch

I built a production-style LLMOps platform. Apps call a central LLM gateway instead of calling model providers directly. The gateway handles API keys, prompt versions, model routing, request logs, latency, failures, and estimated cost.

The main focus is infrastructure: Terraform-managed AWS infrastructure, Kubernetes on EKS, Helm releases, GitHub Actions CI/CD, staged deployments, rollback workflows, OpenTelemetry tracing, Prometheus metrics, Grafana dashboards, Loki logs, External Secrets, and reliability runbooks.

## Portfolio positioning

Pair this project with Proofbase and AgentOps when explaining the portfolio:

- Proofbase: a realistic permission-aware RAG product with citations, scoped retrieval, document workflows, and benchmarked answer quality.
- AgentOps Workflow Platform: a realistic agent workflow product with workflow runs, agent steps, structured generation, retries, tool categories, and per-step costs.
- Production AI Platform: the production LLMOps layer that centralizes model access, cost, latency, errors, traces, secrets, deployments, rollback, and cloud operations.

The clean demo story: Proofbase shows the enterprise RAG product layer, AgentOps shows the agent workflow layer, and Production AI Platform shows how AI workloads are operated responsibly in production. Proofbase and AgentOps are telemetry-connected client apps; the platform centralizes operational visibility without taking over retrieval, citations, workflow execution, prompts, generated outputs, or tool payloads.

## Demo flow

1. Show README architecture diagram.
2. Run local app with Docker Compose.
3. Send a gateway request.
4. Show request in dashboard.
5. Send the local Proofbase demo telemetry event and filter the dashboard to `source_app=proofbase`.
6. Send the local AgentOps demo telemetry event and filter the dashboard to `source_app=agentops`.
7. Explain why Proofbase rows are RAG operations while AgentOps rows are agent-step/workflow-summary operations.
8. Show cost/latency/error metrics.
9. Show CI workflow.
10. Show Terraform modules.
11. Show Helm chart values for dev/staging/prod.
12. Show Grafana dashboard.
13. Show Loki logs by request ID.
14. Show rollback workflow.
15. Show incident runbook, including the external telemetry outage section.

## Screenshots to capture

- Dashboard overview
- Proofbase-filtered dashboard view
- AgentOps-filtered dashboard view
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
- Connected AgentOps Workflow Platform as a telemetry-first client app for centralized agent-step usage, latency, retry, status, token, error, workflow-summary, and estimated-cost visibility while preserving the workflow/orchestration boundary.

## Client App Boundaries

Proofbase remains the AI product layer for permission-aware enterprise RAG. AgentOps remains the agent workflow layer for workflow runs, agent steps, retries, structured generation, tools, and local workflow observability. Production AI Platform remains the operations layer that centralizes telemetry, cost, latency, failures, dashboards, infrastructure, deployment, secrets, and reliability controls.
