# Portfolio Demo Plan

## Goal

Show a recruiter or hiring manager that this is a serious production infrastructure project, not just a small AI app.

## 60-second pitch

I built a production-style LLMOps platform. Apps call a central LLM gateway instead of calling model providers directly. The gateway handles API keys, prompt versions, model routing, request logs, latency, failures, and estimated cost.

The main focus is infrastructure: Terraform-managed AWS infrastructure, Kubernetes on EKS, Helm releases, GitHub Actions CI/CD, staged deployments, rollback workflows, OpenTelemetry tracing, Prometheus metrics, Grafana dashboards, Loki logs, External Secrets, and reliability runbooks.

## Demo flow

1. Show README architecture diagram.
2. Run local app with Docker Compose.
3. Send a gateway request.
4. Show request in dashboard.
5. Show cost/latency/error metrics.
6. Show CI workflow.
7. Show Terraform modules.
8. Show Helm chart values for dev/staging/prod.
9. Show Grafana dashboard.
10. Show Loki logs by request ID.
11. Show rollback workflow.
12. Show incident runbook.

## Screenshots to capture

- Dashboard overview
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
