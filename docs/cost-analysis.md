# Cost Analysis

## Purpose

This document explains expected cloud and LLM costs, the guardrails in the repository, and the cleanup process for development environments.

Cost estimates are directional portfolio estimates, not invoices. They assume `us-east-1`, on-demand pricing, 730 hours per month, low traffic, modest observability retention, and the Terraform defaults in this repository. Before a real deployment, refresh the numbers in the AWS Pricing Calculator and with current AWS pricing pages.

Reference sources:

- Amazon EKS pricing: `https://aws.amazon.com/eks/pricing/`
- Amazon RDS for PostgreSQL pricing: `https://aws.amazon.com/rds/postgresql/pricing/`
- Amazon ElastiCache pricing: `https://aws.amazon.com/elasticache/pricing/`
- Amazon VPC pricing: `https://aws.amazon.com/vpc/pricing/`
- AWS Budgets pricing: `https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/`

## Cost Categories

Cloud cost drivers:

- EKS cluster control plane
- EKS managed node groups
- EBS volumes for worker nodes
- RDS PostgreSQL instance, storage, and backups
- ElastiCache Redis nodes and snapshots
- NAT gateway hourly and data processing charges when enabled
- Application Load Balancer hourly and LCU charges
- ECR image storage
- CloudWatch, Prometheus, Grafana, Loki, and trace/log retention
- Data transfer

LLM usage cost drivers:

- input tokens
- output tokens
- selected provider/model
- retries
- failed requests that reach a provider and still consume tokens
- high-volume client apps or abusive API key usage

## Current portfolio scope (2026-09-08)

The launch preparation now targets **one approved AWS dev/demo environment**.
Staging and production estimates below are retained historical comparisons for
optional configurations, not required deployments or an approved spending plan.
Phase 65 must refresh pricing for the selected single footprint, intended running
period and separately approved cleanup. No resources or cleanup are authorized
by this planning update. See [the completion plan](portfolio-completion-plan.md).

## Environment Cost Estimate

| Environment | Terraform sizing baseline | Monthly estimate | Main cost drivers | Cost posture |
|---|---|---:|---|---|
| local | Docker Compose only | `$0` cloud | Local CPU, disk, and Docker resources | Default development path. |
| dev | 1 EKS cluster, 1-2 `t3.medium` nodes, `db.t4g.micro`, 1 `cache.t4g.micro`, NAT disabled | `$150-$230` | EKS control plane, worker nodes, RDS, Redis, ALB | Smallest practical cloud environment; tear down when idle. |
| staging | 1 EKS cluster, 2 `t3.medium` nodes, Multi-AZ `db.t4g.small`, 2 Redis nodes, 1 NAT gateway | `$300-$500` | EKS, nodes, Multi-AZ data services, NAT, observability | Production-like enough for release rehearsal without prod sizing. |
| prod | 1 EKS cluster, 3 `t3.large` nodes, Multi-AZ `db.t4g.medium`, 2 Redis nodes, 1 NAT gateway | `$700-$1,100` | Larger nodes, Multi-AZ RDS/Redis, NAT, logs/metrics/traces | Conservative portfolio production baseline. |

These ranges intentionally include headroom for EBS, backups, load balancer, registry, and observability storage. They exclude domain registration, paid support plans, high data transfer, and real paid LLM provider usage.

## Terraform Budget Alert

Phase 28 adds an optional AWS Budget module:

- `infra/terraform/modules/budget`
- wired into `dev`, `staging`, and `prod`
- disabled by default
- creates a monthly cost budget when `budget_alert_enabled = true`
- requires at least one alert email before a real plan/apply can succeed

Example environment settings:

```hcl
budget_alert_enabled           = true
budget_monthly_limit_usd       = "75"
budget_alert_threshold_percent = 80
budget_alert_subscriber_emails = ["platform-ops@example.com"]
```

Budget defaults:

| Environment | Monthly budget default | Alert threshold |
|---|---:|---:|
| dev | `$75` | 80% |
| staging | `$250` | 80% |
| prod | `$650` | 80% |

Budget resources are Terraform code only until an approved `terraform apply` is run. Do not use real personal email addresses or account-specific billing contacts in committed examples. If a budget is enabled without subscribers, the reviewed plan/apply should fail instead of silently omitting the guardrail.

## App-Level LLM Cost Tracking

The [Phase 63 local rehearsal](local-recovery-rehearsal.md) uses 20 synthetic
load requests plus a few recovery probes and the mock provider: no paid LLM or
AWS calls. It verifies durable cost records after restore. Mock estimates are
demonstration values, not incurred provider charges.

AWS Budgets are **notifications, not hard spending caps**. Request/concurrency
quotas, bounded retries, maximum replica/node counts and data retention are
separate controls. Redis outages fail admission closed; restored Redis counters
may reset. Deployment and teardown still require explicit approval. Phase 65
refreshes the one-environment estimate and intended running period.

The API already estimates LLM cost per successful gateway request.

Implementation path:

- Java `gateway/MockPricing.java` defines mock token prices, `MockProvider.java`
  estimates usage, and `GatewayRecorder.java` persists request/cost records under
  `apps/api-java/src/main/java/dev/christiankfoury/aiplatform/`.
- `apps/api` remains the historical Python compatibility reference.
- `gateway_requests.estimated_cost_usd` stores request-level cost.
- `cost_records.estimated_cost_usd` stores cost records for usage aggregation.
- `GET /v1/usage/summary` returns total estimated cost.
- The web dashboard shows estimated cost in the summary view.
- Prometheus exposes `llm_gateway_estimated_cost_usd_total`.
- Grafana includes cost panels for 24-hour cost, cost by model, cost per token, and token usage.

Current limitation:

- The first provider is a mock provider with static pricing.
- Real provider pricing must be refreshed from provider billing documentation before enabling paid provider calls.
- External Proofbase telemetry may include estimated chat costs for RAG queries, streaming queries, Markdown cleanup, and query decomposition when Proofbase reports token usage. Proofbase embedding telemetry is accepted as usage/count telemetry but should be labeled unpriced until embedding pricing is configured.
- Estimated costs are for operational visibility, not billing-grade accounting.

## Scaling Cost Assumptions

Application scaling:

- HPA can add API/web replicas when CPU rises.
- PDBs and rolling updates protect availability but can keep extra pods running during disruption.
- More API replicas increase node pressure and may trigger node group scale-out.
- Provider retries increase latency and can increase LLM token cost when a provider charges for failed attempts.

Infrastructure scaling:

- EKS control plane cost is mostly fixed per cluster-hour.
- Worker nodes, RDS class, Redis node count, NAT traffic, and observability retention scale with usage.
- Staging and prod Multi-AZ data services trade higher cost for availability and recovery posture.
- NAT gateway can become expensive for provider egress, image pulls, and package downloads; prefer VPC endpoints where appropriate.

LLM scaling:

- Cost grows with request volume, model choice, prompt size, output size, and retry behavior.
- Prompt templates should stay concise.
- Model routes should default to the smallest acceptable model and reserve larger models for explicit use cases.
- Rate limits protect both reliability and spend.

## Resource Right-Sizing Notes

Dev:

- Keep NAT disabled by default.
- Use `db.t4g.micro`, one Redis cache cluster, short backup retention, and smaller ECR retention.
- Keep node group `min_size = 1` and rely on local Docker Compose for most development.
- Disable or tear down dev cloud resources when not actively demonstrating.

Staging:

- Use smaller production-like shapes: `db.t4g.small`, two Redis cache clusters, two worker nodes, and realistic backup retention.
- Run staging for release validation windows rather than leaving it hot indefinitely when cost matters.
- Keep observability retention long enough for rehearsal, but shorter than prod.

Prod:

- Use conservative node and data-service defaults.
- Keep deletion protection, final snapshots, Multi-AZ data services, and longer secret recovery windows.
- Tune node groups, RDS class, Redis class, and observability retention from measured metrics, not guesswork.
- Use budgets and cost alerts before enabling paid provider integrations.

## Dev Teardown Guidance

Local teardown:

```bash
docker compose down
```

Remove local volumes only when disposable local data can be lost:

```bash
docker compose down --volumes
```

Cloud dev teardown is destructive and requires explicit approval:

1. Confirm no demo, test, or shared validation is using the dev environment.
2. Export approved AWS credentials outside the repository.
3. Capture any needed logs, screenshots, or database snapshots.
4. Confirm state backend access and lock health.
5. Run a reviewed plan:

   ```bash
   cd infra/terraform/environments/dev
   terraform plan -destroy
   ```

6. Run `terraform destroy` only after explicit approval.
7. Confirm ECR images, NAT gateways, load balancers, EBS volumes, RDS snapshots, and Secrets Manager placeholders are intentionally retained or removed according to the plan.

Do not run `terraform destroy` as part of normal Codex phase work.

## Operational Cost Controls

Implemented:

- request-level estimated LLM cost persistence
- usage summary estimated cost
- Prometheus estimated-cost metric
- Grafana cost dashboard panels
- rate limiting by API key
- bounded provider retries
- resource requests/limits
- HPA/PDB posture
- environment-specific Terraform sizing
- ECR image lifecycle retention
- optional AWS Budget Terraform module
- dev teardown guidance

Not yet implemented:

- real provider billing ingestion
- per-project quota enforcement
- automatic budget remediation actions
- cross-account cost allocation reports
- Savings Plans or Reserved Instance purchasing

## README Claim Requirement

Honest README claim:

> The platform tracks estimated LLM usage cost per request and includes environment-specific cloud cost analysis, right-sizing notes, optional AWS Budget alert Terraform code, rate limits, and dev teardown guidance.

Avoid claiming billing-grade metering or automated spend enforcement until those features are implemented.
