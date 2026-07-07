# Decision Log

Use this file to record major architecture decisions.

## ADR-001: Cloud provider

Decision: Use AWS.

Reason:

- Broad market relevance.
- Strong fit for DevOps/cloud roles.
- EKS, ECR, RDS, ElastiCache, IAM, and Secrets Manager map well to the project goals.

Tradeoff:

- AWS can be more complex and costly than local-only or simpler PaaS options.

## ADR-002: Backend framework

Decision: Use FastAPI.

Reason:

- Strong for API development.
- Python fits AI/LLM workflows.
- Easy OpenTelemetry and Prometheus integration.

## ADR-003: Frontend framework

Decision: Use Next.js.

Reason:

- Common in full-stack roles.
- Good dashboard experience.
- Strong TypeScript ecosystem.

## ADR-004: Kubernetes packaging

Decision: Use Helm.

Reason:

- Common in production Kubernetes workflows.
- Supports environment-specific values.
- Works with both GitHub Actions and Argo CD.

## ADR-005: GitOps

Decision: Add Argo CD as an optional GitOps deployment path.

Reason:

- Keeps the core CI/CD path simpler first.
- Adds advanced platform credibility near the end.
- Reuses the Helm chart rather than introducing a second deployment package.

Tradeoff:

- GitHub Actions and Argo CD must not both continuously control the same Helm release in the same namespace.


## ADR-006: Relationship to Proofbase and RAG scope

Decision: Keep this project focused on production LLMOps infrastructure and keep advanced RAG capabilities in Proofbase.

Reason:

- Proofbase already demonstrates document ingestion, vector retrieval, citations, permission filtering, memory safety, and benchmark-driven RAG evaluation.
- This project should demonstrate a different portfolio strength: operating AI workloads with a gateway, API keys, prompt/model routing, observability, secrets, CI/CD, Kubernetes, Terraform, rollback, and cost controls.
- Separating the projects makes the portfolio easier to explain: one project is the AI application, the other is the production platform layer.

Tradeoff:

- The platform will be less impressive as a standalone AI product, but stronger as infrastructure and LLMOps evidence.

Future integration:

- Proofbase should connect through telemetry first, then gateway routing later. In the telemetry-first step, Proofbase keeps owning retrieval, citations, permission filtering, memory, and evaluation, while this platform centralizes cost, latency, token, error, and request visibility. Gateway-routed model calls can follow after the gateway supports Proofbase's richer request contract.
