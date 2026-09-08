# Backup and Restore

## Purpose

This document defines the recovery posture for the Production AI Platform. It covers PostgreSQL backups, restore runbooks, Terraform state recovery, Redis persistence decisions, and disaster recovery assumptions.

All cloud restore actions are approval-gated. This repository may document and validate recovery paths, but it must not run `terraform apply`, mutate AWS resources, rotate secrets, or redirect production traffic without explicit human approval.

## Recovery Targets

| Environment | RDS backup retention | Redis snapshot retention | RTO target | RPO target | Notes |
|---|---:|---:|---:|---:|---|
| dev | 1 day | 1 day | 1 business day | 24 hours | Cost-minimized and rebuildable. Data loss is acceptable for local/dev validation. |
| staging | 7 days | 7 days | 4 hours | 24 hours | Used for restore rehearsal and release validation. |
| prod | 14 days | 14 days | 2 hours | 1 hour or better when RDS PITR is available | Portfolio target, subject to an approved live recovery exercise before real production claims. |

The Terraform defaults are encoded in:

- `infra/terraform/environments/dev/terraform.tfvars.example`
- `infra/terraform/environments/staging/terraform.tfvars.example`
- `infra/terraform/environments/prod/terraform.tfvars.example`
- `infra/terraform/modules/database`
- `infra/terraform/modules/redis`

## Database Backup Strategy

PostgreSQL is the system of record for API keys, prompt versions, model routes, request logs, audit logs, and cost records.

The RDS module configures:

- private subnets only
- encrypted gp3 storage
- AWS-managed master password through `manage_master_user_password`
- automated backup retention per environment
- backup and maintenance windows
- `copy_tags_to_snapshot = true`
- deletion protection for staging and prod by default
- final snapshots for staging and prod by default
- Multi-AZ for staging and prod by default

Non-dev backup posture:

- Staging keeps 7 days of automated backups.
- Prod keeps 14 days of automated backups.
- Staging and prod enable deletion protection and do not skip final snapshots.
- Prod restore targets should be validated in staging before production cutover whenever the incident allows time.
- Destructive migrations require an explicit pre-migration backup or snapshot plan before execution.

Operational rules:

- Never commit database dumps, connection strings, passwords, or temporary restore credentials.
- Restore into a new RDS instance first; do not overwrite the failed source during triage.
- Treat secret updates, endpoint changes, DNS changes, and production traffic shifts as approval-gated operations.
- Keep the old database available until post-restore validation is complete and a rollback decision is recorded.

## Database Restore Runbook

Use this path when data corruption, accidental deletion, failed migration, or database infrastructure failure requires recovery.

1. Declare the incident severity and assign an incident lead.
2. Freeze risky writes if the application is still online. Options include disabling deploys, pausing traffic at ingress, or temporarily scaling API writes down after approval.
3. Identify the target recovery point:
   - last known-good timestamp
   - latest automated backup
   - manual snapshot taken before a migration
4. Restore RDS to a new instance or cluster endpoint. Use the AWS console, CLI, or Terraform import workflow according to the approved operations process.
5. Keep the restored database private in the same VPC/subnet/security-group posture as the source.
6. Retrieve the restored database endpoint through AWS-managed outputs or console metadata. Do not print credentials in logs.
7. Create or update the runtime database secret through the approved secret-management path. Do not commit the secret value.
8. Use the Java migration image's read-only `verify-schema` command against the restored target. Flyway is the sole migration owner after cutover. If a compatible forward migration is needed, review it and run the separate migration job; never run Alembic on a Flyway-owned database or downgrade its schema.
9. Point a staging or temporary validation deployment at the restored database.
10. Validate:
    - API readiness passes
    - gateway smoke request succeeds
    - request log writes succeed
    - dashboard usage summary loads
    - error rate and database alerts are normal
11. For production cutover, obtain explicit approval to update the production runtime secret or traffic target.
12. Restart or roll the API deployment so it reads the approved restored endpoint.
13. Monitor API 5xx rate, database availability, latency, and request-log writes for at least one release window.
14. Record the recovery timestamp, restored source, validation result, and residual data-loss window in the incident timeline.

Approval gates:

- Restoring an AWS RDS instance creates paid resources.
- Updating production runtime secrets can affect live traffic.
- Redirecting production traffic can cause downtime.
- Destroying the failed source database or old snapshots is destructive.

## Local Restore Rehearsal

Use [the Phase 63 rehearsal](local-recovery-rehearsal.md). It creates a unique
Compose project, uses only the mock gateway and synthetic seeds, stops writes
before `pg_dump -Fc`, then restores with `pg_restore --exit-on-error --no-owner
--no-acl` into an empty PostgreSQL service. It never drops, cleans, overwrites or
attaches to an existing database. Python captures binary dump bytes directly;
PowerShell text redirection is not used for the custom-format archive.

The restored row counts and stable hashes cover every application table and
Flyway history. A temporary Java API then proves readiness and a new durable
gateway write against the recovered database. Both database volumes and stopped
containers remain available; cleanup or database deletion needs separate approval.
The dump remains in ignored `.maven-cache/`, contains synthetic fixture data only,
and must not be committed. Never reuse this script to back up a real database.

The measured local timings are not AWS RTO/RPO, PITR or production-SLA evidence.
Monitoring alert resolution is deferred under Phase 62 and required before Phase 66.

## Terraform State Recovery

Terraform state is operationally sensitive because it maps cloud resources to code.

Baseline state posture:

- Each environment has a `backend.hcl.example` placeholder for S3 state and DynamoDB locking.
- Real backend bucket names, lock table names, and account-specific values must stay outside Git.
- State buckets should have encryption, versioning, access logging where available, and least-privilege IAM.
- State lock tables prevent concurrent writes.
- `.tfstate`, `.tfstate.backup`, generated `backend.hcl`, and populated `.tfvars` files must not be committed.

Recovery path:

1. Stop Terraform writes for the affected environment.
2. Identify the last known-good state object version in the remote state bucket.
3. Copy the suspected-bad state object aside before restoration.
4. Restore the last known-good object version in S3.
5. Reinitialize locally with the approved backend config.
6. Run `terraform state list` and `terraform plan` to assess drift.
7. If resources exist but are missing from state, use `terraform import` only after approval and with an import checklist.
8. If a lock is stale, verify no Terraform run is active before force-unlocking.
9. Record the state object version, operator, plan result, and any imports in the incident timeline.

Never hand-edit state as a first response. Prefer object-version restore, `terraform import`, and small reviewed state operations.

## Redis Persistence Decision

Redis is not the source of truth for this platform.

Current intended uses are:

- rate-limit counters
- short-lived operational cache
- queue or coordination state if added later

Decision:

- PostgreSQL remains the durable store for platform records.
- Redis data is treated as reconstructable ephemeral state.
- ElastiCache snapshots are retained per environment to support operational recovery and debugging, but losing Redis should not lose durable business data.
- If a future phase adds durable asynchronous jobs, use PostgreSQL outbox records, SQS, or another durable queue before claiming Redis-backed job durability.

Tradeoff:

- Ephemeral Redis keeps recovery simpler and lowers operational burden.
- Snapshot retention helps with accidental flushes or environment diagnostics.
- The cost is that rate-limit counters and cache state may reset during Redis recovery, which is acceptable for this portfolio baseline.

## Disaster Recovery Assumptions

Honest baseline:

- The platform is single-region in AWS.
- Staging and prod default to Multi-AZ RDS and Redis, but not multi-region active-active.
- No automated cross-region database replication is configured.
- DNS, TLS, and custom domains are optional and environment-specific.
- ECR images are immutable and can also be rebuilt from Git SHAs if the registry is unavailable.
- EKS clusters, networking, IAM, data services, secrets placeholders, Helm releases, and monitoring configuration are recoverable from Terraform, Kubernetes manifests, Helm chart values, and GitHub Actions workflows.
- Secret values must be restored through AWS Secrets Manager or the approved secret process; they are intentionally not recoverable from Git.

Acceptable portfolio claim:

- The project documents restore paths, RTO/RPO targets, and infrastructure-as-code recovery.
- It is not claiming tested multi-region disaster recovery unless a future phase adds and rehearses it.

## Validation Checklist

Documentation-only validation:

```bash
git diff --check
rg -n "RTO|RPO|restore|backup|Terraform state|Redis" docs README.md phases-progress.md
```

Infrastructure validation when Terraform changes are made:

```bash
terraform fmt -recursive infra/terraform
terraform init -backend=false
terraform validate
```

Run Terraform validation separately for each environment root. Do not run `terraform apply` as part of this checklist.
