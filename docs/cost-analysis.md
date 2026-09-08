# Cost analysis: one AWS dev/demo

Planning date: **2026-09-08**. Launch is **blocked**, not approved. The proposal is
one private `us-east-1` dev/demo for **48 hours**, including setup and rollback.
Expected scenario cost is approximately **USD 30**, with a proposed **USD 50**
review envelope. Leaving the same footprint running for 730 hours is about
**USD 322**, or **USD 425** with rounded contingency. No resources were created.

These are calculations from public AWS prices and explicit usage assumptions,
not an invoice or an authenticated AWS Pricing Calculator plan. Before approval,
refresh the rates for the actual account/region/date and complete the missing
inputs in [the launch checklist](aws-launch-checklist.md). No free-tier credits,
Savings Plans, Spot discounts, tax or currency conversion are assumed.

## Priced footprint and arithmetic

The model follows current dev Terraform: two `t3.medium` workers, private EKS API,
one shared NAT/EIP, Single-AZ RDS and one Redis node. It also budgets a proposed
internal ALB, private ephemeral runner and monitoring/storage/secret allowances
required for the complete demo. Those additions are not all enabled or implemented
by the current root; they require approved inputs/bootstrap. Staging/prod are
owner-skipped and have **no allocation** in this estimate.

| Resource / allowance | Quantity x unit rate USD | 48 hours | 730-hour month |
|---|---|---:|---:|
| [EKS standard support](https://aws.amazon.com/eks/pricing/) | 1 x 0.10/hour | 4.80 | 73.00 |
| [Worker nodes: t3.medium](https://docs.aws.amazon.com/prescriptive-guidance/latest/optimize-costs-microsoft-workloads/right-size-selection.html) | 2 x 0.0416/hour | 3.99 | 60.74 |
| [Worker root EBS allowance](https://aws.amazon.com/ebs/pricing/) | 80 x 0.10/month | 0.53 | 8.00 |
| [RDS db.t4g.micro Single-AZ](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) | 1 x 0.016/hour | 0.77 | 11.68 |
| [RDS gp3 GB](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) | 20 x 0.115/month | 0.15 | 2.30 |
| [Redis cache.t4g.micro](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonElastiCache/current/us-east-1/index.json) | 1 x 0.016/hour | 0.77 | 11.68 |
| [One shared NAT](https://aws.amazon.com/vpc/pricing/) | 1 x 0.045/hour | 2.16 | 32.85 |
| [NAT public IPv4](https://aws.amazon.com/vpc/pricing/) | 1 x 0.005/hour | 0.24 | 3.65 |
| [Internal ALB](https://aws.amazon.com/elasticloadbalancing/pricing/) | 1 x 0.0225/hour | 1.08 | 16.43 |
| [ALB capacity: 1 LCU allowance](https://aws.amazon.com/elasticloadbalancing/pricing/) | 1 x 0.008/hour | 0.38 | 5.84 |
| [Private t3.large runner allowance](https://docs.aws.amazon.com/prescriptive-guidance/latest/optimize-costs-microsoft-workloads/right-size-selection.html) | 1 x 0.0832/hour | 3.99 | 60.74 |
| [Runner gp3 GB allowance](https://aws.amazon.com/ebs/pricing/) | 30 x 0.08/month | 0.16 | 2.40 |
| [Monitoring gp3 GB allowance](https://aws.amazon.com/ebs/pricing/) | 40 x 0.08/month | 0.21 | 3.20 |
| [ECR GB allowance](https://aws.amazon.com/ecr/pricing/) | 10 x 0.10/month | 0.07 | 1.00 |
| [Total secret allowance](https://aws.amazon.com/secrets-manager/pricing/) | 6 x 0.40/month | 0.16 | 2.40 |
| [EKS KMS key](https://aws.amazon.com/kms/pricing/) | 1 x 1.00/month | 0.07 | 1.00 |
| **Base subtotal (sum before rounding)** | | **19.52** | **296.90** |
| Variable usage + retained-data allowance | Scenario allowance, not a rate quote | 10.00 | 25.00 |
| **Scenario estimate** | | **29.52** | **321.90** |
| **Proposed review envelope** | Rounded contingency; not an enforced cap | **50.00** | **425.00** |

Hourly items multiply quantity x rate x hours. Storage/secret/key items use the
730-hour planning convention, quantity x monthly rate x hours / 730; actual AWS
billing periods, minimums and rounding can differ. Sum unrounded lines before
rounding the subtotal. [Machine-readable arithmetic and pricing provenance](phase-reviews/phase-65-cost-estimate.json)
retain quantities/rates, source URLs, current RDS/Redis SKUs, publication dates and
source hashes. Both price lists were retrieved publicly without credentials.
RDS/Redis standard node rates are USD 0.016/hour; extended-support SKUs were
explicitly excluded from the base estimate. Supported versions remain a preflight gate.

The worker root volume type is not explicitly pinned by the current node-group
module. Budget its 80 GiB at the higher gp2 example rate of USD 0.10/GB-month;
confirm actual encrypted volume type from the approved launch template before
apply. Runner and monitoring gp3 assumptions use USD 0.08/GB-month with baseline
IOPS/throughput only. No custom storage optimization is introduced by this phase.

## Allowances, omissions and capacity limits

- The private runner is conservatively priced for the whole window, with fresh
  ephemeral execution instances and no ambient release-job AWS credentials. The
  runner manager/access path is an owner input, not provisioned by this repository.
  Reusing a trusted private runner can reduce this cost after review.
- Monitoring's 40 GiB and two extra secret containers above runtime/web/migration
  and the RDS-managed master secret are planning allowances. Phase 62 must settle
  final PVCs, retention, credentials and CPU/memory fit; no prototype was adopted.
  The EKS envelope-key price includes one new key; extra customer-managed keys and
  rotations increase cost.
- The USD 10 two-day / USD 25 monthly allowance covers modest NAT processing,
  internet/cross-AZ transfer, CloudWatch ingestion/query/storage, S3 state and ALB
  logs/requests, secret/KMS API requests, private-zone charges if needed, and
  retained snapshot/ECR/evidence storage. These are **planning reserves**, not
  measured consumption or a claim that all those services are free.
- For scale: 10 GB of NAT processing alone is USD 0.45 at the current VPC rate.
  A full billing-month private zone, a retained 20 GiB database snapshot, modest
  ECR/log storage and API calls can continue after the two-day window; the reserve
  allows for one small synthetic snapshot/evidence set retained for 30 days.
  The cleanup owner must inventory actual retained bytes and reprice anything
  above that allowance. A stopped workload does not delete or stop billing storage.
- Existing approved domain/certificate/IdP and private network connectivity are
  assumed **available inputs**, not newly purchased free services. Registration,
  a new private CA, VPN/Resolver appliances, paid IdP, GitHub protection-plan or
  hosted runner-service fees, support, tax and paid LLM usage are excluded.
  If needed, quote and add them before approval. No public ALB IPv4s are included;
  the proposal uses an internal ALB. Public exposure requires separate approval.
- Current dev starts at two nodes, min 1/max 3, with one API/web replica and HPA
  disabled. No cluster autoscaler is installed by this phase. An extra approved
  `t3.medium` plus 40 GiB at the root-disk allowance adds about USD 2.26/48 hours
  or USD 34.37/month. It does not prove monitoring or rolling-surge capacity.
- RDS storage may grow from 20 to 50 GiB: the extra 30 GiB adds USD 3.45/month.
  Burstable CPU credits, more replicas, extended support, higher log volume, NAT
  cross-AZ paths or retained data can exceed the reserve. EKS standard support is
  USD 0.10/hour; extended support is USD 0.60/hour. Check service/version eligibility
  before creation and use bounded synthetic traffic.

## Budget notifications and operational controls

The Terraform budget is disabled until approved, defaults to USD 75/month with an
80% threshold and has no subscriber. That default is not a funded monthly running
budget. The current module has **no cost filter**: its environment-prefixed name does not
limit it to project charges. Proposed owner review: use a USD 50 account-wide alert
only for a dedicated demo account; otherwise select an appropriate account threshold
or separately review a project-filter implementation before launch. Confirm the
recipient and review project/account spend at bootstrap, after the demo and at the
cleanup window. A longer approved runtime needs a revised limit/date. Do not put
personal billing email addresses in Git.

AWS Budgets are **notifications, not hard spending caps**. Quotas, fixed replica
counts, node bounds, retry/concurrency/rate limits and explicit retention are
separate controls. A missing notification must not be treated as permission to
keep running. Cleanup needs its own explicit approval and may retain charges.
See [gated cleanup](aws-launch-checklist.md#cleanup-plan-separate-approval-no-deletion-now).

## LLM accounting and evidence limits

The Java gateway currently uses `MockCompletionProvider` and `MockPricing`.
`GatewayRecorder` stores request-level estimates and cost records; do not sum
both representations into a double-counted total. Proofbase/AgentOps telemetry
is best-effort and operational only; missing or aggregate-only token/cost data
must remain unknown/unpriced where appropriate. No paid provider is enabled.

[Phase 63](phase-reviews/phase-63.md) measured a mock total of USD 0.000120 and
restored 24 request/cost rows. These were not incurred provider charges. The
[default dashboard captures](assets/screenshots/phase-64.md) are fixed fixtures;
actual usage needs OIDC/project grants. The monitoring prototype's historical
cost panels are not proof of final image eligibility or cloud billing accuracy.

This estimate replaces the earlier USD 150-230 dev / NAT-disabled range, which
no longer matched current Terraform. Historical staging/prod comparisons remain
in Git history and their phase reviews; they are not this release's spending plan.
