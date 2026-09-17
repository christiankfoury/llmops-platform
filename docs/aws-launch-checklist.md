# Single AWS dev/demo launch checklist

Decision, 2026-09-08: **BLOCKED. Preparation does not authorize deployment.**
Phases 63-65 prepare one private dev/demo environment. Phase 62 remains incomplete;
its monitoring fixes/custom rebuilds are deferred, with no risk acceptance. Stop
before Phase 66 until the owner supplies setup inputs, the blockers below close,
and the exact change/cost package receives explicit approval.

## Proposed change and cost boundary

- Region: `us-east-1`, proposed from current dev defaults; account not supplied.
- Lifetime: one 48-hour window from first resource creation, including bootstrap,
  demonstration and rollback. Start/end timestamps and cleanup owner are unset.
- Current Terraform dev: one VPC across two AZs, two public and two private subnets,
  one shared NAT/EIP, private EKS API, two on-demand `t3.medium` workers with 40 GiB
  roots (min 1/max 3), one Single-AZ `db.t4g.micro` PostgreSQL instance with 20 GiB
  gp3 (autoscale ceiling 50 GiB), one `cache.t4g.micro` Redis node, three ECR repos,
  three secret containers plus the RDS-managed master secret, one EKS KMS key,
  scoped IAM/access entries and optional account-wide budget notifications (the
  module has no project cost filter).
- Proposed additions to the initially disabled inputs: protected GitHub roles,
  one **internal** ALB with two target groups and one TLS listener, approved
  certificate/hostnames/access-log bucket/client CIDRs, and a budget recipient.
  `load_balancing=null`, roles disabled and budget disabled are current defaults;
  they are placeholders, not a complete launch configuration.
- Bootstrap outside this root: encrypted/versioned private state bucket and
  locking; GitHub OIDC provider; a trusted ephemeral private Linux amd64 runner
  (priced as one `t3.large` plus 30 GiB disk for the whole window); identity/TLS
  setup; controller/network/trust releases; final eligible monitoring delivery.
- Planning allowances: 40 GiB monitoring PVCs, 10 GB ECR, six total secrets,
  modest logs/requests/transfer/retained snapshots. These are cost assumptions,
  not adoption of the dirty Phase 62 prototype or a proven final capacity fit.
- [Estimate and sources](cost-analysis.md): USD **29.52** for the 48-hour scenario,
  including variable/retained-data allowance. Proposed review envelope **USD 50**;
  not approved and not an enforced cap. About USD 321.90/month if left running,
  before contingency. New domain/IdP/private connectivity or paid runner-service
  fees need a separate quote and repricing; no such service is assumed free.

No staging/prod deployment, public endpoint, paid LLM adapter or customer data is
included. One API/web replica and disabled HPA are current dev settings. This is
not HA: shared NAT, Single-AZ data services and single replicas have outage limits.
Before approval, verify allocatable CPU/memory/pod/IP/EBS limits against the final
monitoring requests and rolling-update/migration surge. If two nodes do not fit,
review a revised size/cost; the optional third node is not automatically authorized.

## Inputs and blockers to close

All unchecked items are **unverified**, not passed. Values belong in the approved
private setup record; never send credentials through chat, Git, screenshots or logs.

| Gate / owner input | Required evidence or decision | Current state |
|---|---|---|
| Monitoring / owner | Resume only on owner direction; close final image/security, compatibility, immutable delivery/SBOM, mandatory monitoring CI and private transport/storage/credential checks in the [backlog](security/monitoring-vulnerability-backlog.md) | BLOCKED, deferred; no exceptions |
| AWS account and region | Intended account ID, approved role/profile, billing owner, region and 48-hour timestamps; verify identity privately before any account operation | Missing |
| Current release | Full candidate SHA and successful current CI run; unexpired, verified API/migration/web OCI digests, chart/value hashes and schema contract; qualified compatible rollback SHA/run retained | Preparation CI recorded in [review](archive/phase-reviews/phase-65.md); refresh at launch |
| Regional compatibility | EKS 1.36 standard support, exact five add-on builds, AL2023 amd64 availability, RDS 16.15/class/storage and Redis 7.2/node/snapshot support | Unverified; version syntax fixtures are not availability evidence |
| Quota and capacity | EKS clusters/nodes, EC2 Standard on-demand vCPUs (at least 6 for two workers + runner; 8 if third node approved), EIP/NAT, ALB/targets, RDS, ElastiCache, ENIs/subnet IPs and EBS capacity | Unverified; headroom and other account workloads must be counted |
| Network/access | CIDR conflict check for `10.20.0.0/16`, private DNS/EKS connectivity, approved client ranges, NAT egress; secure operator path to internal ALB and IdP | Missing; do not expose EKS to fix a disconnected runner |
| State/bootstrap | Existing or separately approved S3 backend, encryption/versioning/TLS/public-blocking/native lock permissions, recovery owner and trusted bootstrap role; account-wide GitHub OIDC provider | Missing; no backend initialized or authenticated plan run |
| Runner/GitHub | Ephemeral runner image/provenance/lifecycle and private routes; supported private-repository environment protections; `dev-publish`, `dev-migration`, `dev` with main-only branches, required reviewers, no self-review/admin bypass | No deployment environments at Phase 64 readback; setup not authorized |
| HTTPS/identity | Two approved HTTPS origins, certificate ARN, DNS ownership/trust path, ALB log bucket; IdP issuer/audience/JWKS/client/callback, project grants and private browser access | Missing. Internal ALB still needs trusted HTTPS; public access or real DNS/TLS changes need separate approval |
| Database/secrets | Separate runtime and migration-owner roles; reviewed grants; seven runtime, three migration and two web-session properties; Redis ephemeral token delivery; approved synthetic smoke key/project | Missing. Real secret creation/change requires approval; no AWS `seed-local` |
| Cost/data/cleanup | Approve exact resource plan and USD envelope, budget subscriber/threshold, monitoring/log retention, snapshot/evidence retention, cleanup window and named owner | Proposal only; cleanup deletion requires separate approval |

The current repository's environment example deliberately uses account `000000000000`
and example domains. Do not make up executable `dev.json`, add-on versions, secrets
or real backend settings to complete this table. Confirm GitHub account features
support the required protection checks; unavailable protection is a blocker, never
a reason to relax them. Runner bootstrap/admin credentials must not be available
to ordinary release jobs.

## Safe preflight, after owner setup

Only public unsigned pricing reads were used; no authenticated AWS API or
Terraform plan was executed for Phase 65. These are
read-only checks for the approved account profile, not recorded results:

```sh
aws sts get-caller-identity --profile APPROVED_PROFILE
aws eks describe-cluster-versions --cluster-versions 1.36 --region us-east-1 --profile APPROVED_PROFILE
aws eks describe-addon-versions --kubernetes-version 1.36 --region us-east-1 --profile APPROVED_PROFILE
aws rds describe-orderable-db-instance-options --engine postgres --engine-version 16.15 --db-instance-class db.t4g.micro --region us-east-1 --profile APPROVED_PROFILE
aws elasticache describe-cache-engine-versions --engine redis --engine-version 7.2 --region us-east-1 --profile APPROVED_PROFILE
aws ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=instance-type,Values=t3.medium,t3.large --region us-east-1 --profile APPROVED_PROFILE
aws service-quotas list-service-quotas --service-code ec2 --region us-east-1 --profile APPROVED_PROFILE
```

Also check the service-specific quotas above, support dates and usable subnet/AZ
capacity; an instance offering does not guarantee launch capacity. Record sanitized
results and exact add-on versions. Keep account details/access metadata private.
Official references: [EKS lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html),
[regional add-on builds](https://docs.aws.amazon.com/cli/latest/reference/eks/describe-addon-versions.html),
[RDS orderable options](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-orderable-db-instance-options.html).

Use the existing [offline validation commands](aws-bootstrap.md#offline-validation)
with pinned tools and backend disabled. After backend/access approval, prepare a
read-only saved plan using a restricted local path outside Git and approved secret
delivery. Never log plan JSON/state or include them in CI artifacts. Review account,
region, all creates/changes/deletes, secret handling, node/PVC capacity, role trust,
load-balancing ownership and full incremental cost. A plan's success is not apply
approval. Any unexpected existing resource, deletion or replacement needs review.

## Ordered deployment and bounded evidence (Phase 66 only)

Follow [AWS bootstrap](aws-bootstrap.md#ordered-approval-gated-bootstrap) and the
[immutable release runbook](immutable-release-runbook.md); these steps summarize
that sequence without running it or removing the hard holds.

1. Close every gate; review actual foundation plan, resource inventory, cost,
   secret/DNS/TLS operations and rollback/cleanup boundaries with the owner.
   Obtain explicit approval before any paid creation, apply or real secret change.
2. Apply only the approved foundation with `bootstrap_addons_enabled=false`.
   Install namespace/RBAC/trust/DNS/network bootstrap first. Review and approve
   the second plan enabling CoreDNS/CSI/metrics-server after strict CNI policies.
   Verify private endpoint access, DNS, allowed/denied network traffic and CSI.
3. Install reviewed scoped ESO controllers, approved secret versions and database
   grants. Verify Ready without revealing values; prove hostname-verified RDS
   and Redis TLS. Install network Services/policies and approved Terraform ALB.
   Follow exact-target admission/controller ordering; create approved TGBs before
   app pods so readiness gates are injected. Keep Ingress writes denied.
4. Install the **eligible final** monitoring release only after Phase 62 closes.
   Verify PVC sizing/retention, private access and credentials. No prototype image
   or deferred finding may be substituted. Review protected environment/runner
   checks and the separate approved change to remove cloud-job holds.
5. Prepare the nonsecret `infra/release/environments/dev.json` from actual outputs.
   Reverify current CI and publish the same OCI bytes to ECR; run the isolated
   Flyway V2 migration/verify Job, then the immutable application Helm release.
   No rebuild during promotion, destructive migration or second migration owner.
6. Capture one bounded synthetic request/telemetry/auth/dashboard demonstration,
   searchable correlated logs/traces, one fired/resolved alert and verified cloud
   backup settings. Record exact images, CI/release receipts, timestamps, actual
   resource/cost inventory and limitations. Reuse Phase 63 local restore evidence;
   no separate cloud restore campaign or staging environment is required.
7. Perform one approved compatible application rollback: retained qualified SHA
   and CI run, schema V2 `verify-schema` only, older image digests, readiness and
   functional smoke. Never downgrade/repair/clean Flyway history. On failure retain
   evidence and choose a reviewed compatible rollback or forward fix; do not bypass
   the verifier, clear finalizers or delete failed Jobs/data.

Verify actual RDS backup retention (current default one day), encryption, latest
restorable point and snapshot posture; verify Redis snapshot behavior and counter
reset implications. Current dev disables DB deletion protection and skips a final
snapshot. Those defaults do not authorize data loss: choose an explicit snapshot
and retention decision before cleanup. [Local recovery](archive/phase-reviews/phase-63.md)
proved 24 request/cost rows and a new write; it is not cloud RTO/RPO or PITR proof.

## Cleanup plan: separate approval, no deletion now

At the agreed end time, review the inventory and obtain **separate deletion
approval naming exact resources and retained data**. A 48-hour proposal is not an
automatic teardown authorization; charges continue while resources are retained.

1. Preserve sanitized receipts, metrics and actual costs. Inventory account/region,
   Terraform resources, Kubernetes PVC/EBS ownership, RDS/Redis snapshots, ECR,
   logs, runners, NAT/EIP, IAM, secrets, KMS and backend. Separate shared resources.
2. Agree whether to retain a final synthetic RDS snapshot and any PVC data; verify
   retained evidence/backups before approved deletion. Default proposal: retain
   one snapshot and minimal sanitized release evidence for 30 days, then request
   deletion approval again. Do not shorten secret recovery/KMS windows to save time.
3. Stop new releases/workload after approval. Keep the target controller alive
   while approved bindings deregister; verify empty targets/finalizers before
   controller removal. ALB deletion protection must be changed only in a separately
   approved cleanup plan. Do not force finalizers, namespaces or Helm ownership.
4. Review a scoped Terraform destroy plan privately and obtain execution approval.
   Apply only that approved cleanup. ECR `force_delete=false`, retained volumes,
   snapshots and secret recovery windows may intentionally prevent full removal;
   never auto-purge or change protections to force success.
5. Verify residual billable items and tag-filtered costs after billing catches up.
   Retained snapshots/EBS/ECR/logs/secrets and shared state/KMS may still cost money.
   Preserve the backend and shared GitHub OIDC/identity infrastructure unless their
   owners explicitly approve deletion. Record what remains, cost and next owner date.

The handoff stops here before Phase 66. Phase 62 remains blocked, 67-68 remain
owner-skipped. Source publication may precede AWS under the owner-approved
[publication plan](publication-decisions.md); final visibility approval remains separate.
Phase 69 cloud closeout still requires the approved AWS evidence.
