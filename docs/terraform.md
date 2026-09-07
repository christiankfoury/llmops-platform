# Terraform

Current AWS load-balancing ownership is defined in [the TargetGroupBinding design](targetgroupbinding-design.md): Terraform owns ALB/listeners/rules/security groups/target groups; the pinned controller has no Ingress writes and only exact-group registration permissions. Bootstrap controls immutable bindings and readiness admission. Historical Ingress examples below do not supersede this approval-gated sequence.

This repository includes AWS foundation Terraform as code only. Do not run `terraform apply` or create cloud resources without explicit human approval.

## Scope

Current modules:

- `modules/network`: VPC, public subnets, private subnets, route tables, optional NAT gateway
- `modules/registry`: ECR repositories for API and web images with immutable tags and scan-on-push
- `modules/secrets`: AWS Secrets Manager placeholder secrets without secret values
- `modules/iam`: optional GitHub Actions OIDC role for ECR publishing and dev EKS kubeconfig access
- `modules/cluster`: EKS cluster, managed node groups, cluster/node IAM roles, and OIDC provider for workload identity
- `modules/database`: private RDS PostgreSQL with encrypted storage, AWS-managed master password, backups, and security group ingress from EKS
- `modules/redis`: private ElastiCache Redis replication group with encryption, snapshots, and security group ingress from EKS
- `modules/budget`: optional monthly AWS Budget alert, disabled by default

Current environments:

- `environments/dev`
- `environments/staging`
- `environments/prod`

Kubernetes workload manifests, Helm packaging, deployment workflows, and security controls are implemented elsewhere in the repository and are wired to the same dev/staging/prod environment model.

## Credentials

Terraform reads AWS credentials from the standard AWS provider chain. For local validation, credentials are not required if you only run `terraform init -backend=false`, `terraform fmt`, and `terraform validate`.

For approved plan/apply work, use environment-scoped credentials outside the repository:

```bash
export AWS_PROFILE=replace-with-approved-profile
export AWS_REGION=us-east-1
```

Never commit AWS access keys, account IDs, provider credentials, or generated `.tfvars` files containing sensitive values.

## Remote State

Each environment includes `backend.hcl.example` with placeholder S3 and DynamoDB names.

After an approved state backend exists, initialize an environment with:

```bash
cd infra/terraform/environments/dev
terraform init -backend-config=backend.hcl
```

For local structural validation without remote state:

```bash
cd infra/terraform/environments/dev
terraform init -backend=false
terraform validate
```

If Terraform is not installed locally, use the official Docker image from the repository root:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace hashicorp/terraform:1.10.5 fmt -recursive infra/terraform
docker run --rm -v "$PWD:/workspace" -w /workspace/infra/terraform/environments/dev hashicorp/terraform:1.10.5 init -backend=false
docker run --rm -v "$PWD:/workspace" -w /workspace/infra/terraform/environments/dev hashicorp/terraform:1.10.5 validate
```

Repeat `init -backend=false` and `validate` for staging and prod.

Terraform state recovery is documented in `docs/backup-restore.md`. In short: stop Terraform writes, restore the last known-good versioned state object from the approved remote backend, run `terraform plan` to assess drift, and use `terraform import` only after review. Do not commit generated state files or populated backend config.

## EKS Cluster

Phase 12 wires the EKS module into every environment.

The cluster module creates:

- EKS control plane
- EKS cluster IAM role
- managed node group IAM role
- managed node groups in private subnets
- EKS OIDC provider for IAM Roles for Service Accounts
- control plane log type configuration

Environment defaults:

- dev: two availability zones, one small on-demand node group, private endpoint access by default
- staging: two availability zones, one on-demand node group, full control plane logging
- prod: three availability zones, larger on-demand node group, private endpoint access by default

`kubernetes_version` defaults to `null` so AWS selects the default supported EKS version at creation time. Pin a version per environment before any approved real deployment if release control requires it.

The Kubernetes provider is configured from the EKS cluster data sources so later Kubernetes and Helm phases can use the same environment root after the cluster exists.

Cluster access after an approved apply:

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name production-ai-platform-dev-eks
```

Replace the environment and region as needed. Production endpoint defaults are private, so access requires network reachability to the VPC.

## Environment Defaults

Dev is cost-conscious by default:

- two availability zones
- NAT gateway disabled
- shorter ECR image retention
- 7-day secret recovery window
- optional monthly budget alert defaulting to `$75`, disabled until an alert email is supplied and apply is approved

Staging and prod are more production-like:

- staging uses two availability zones and NAT enabled
- prod uses three availability zones and NAT enabled
- longer ECR retention
- longer secret recovery windows
- optional monthly budget alert defaults of `$250` for staging and `$650` for prod, disabled until alert emails are supplied and apply is approved

These defaults are code only. Applying them creates paid AWS resources and requires explicit approval.

## Secrets

The secrets module creates only secret containers/placeholders in AWS Secrets Manager. It does not create `aws_secretsmanager_secret_version` resources and does not store secret values in Terraform state.

Secret values must be written through an approved secure process outside this repository.

Phase 24 extends the secrets module with an optional External Secrets Operator IAM role. The role trusts the EKS OIDC provider and the `external-secrets/external-secrets` service account, and its read policy is scoped to the environment's Secrets Manager ARNs.

The database module uses RDS `manage_master_user_password`, so AWS manages the generated master password in Secrets Manager. Terraform outputs the managed secret ARN as sensitive and does not accept or store a plaintext database password.

## IAM

The IAM module can create a GitHub Actions OIDC provider and CI/CD role, but it is disabled by default in every environment.

When enabled, the role is restricted to:

- this repository
- the `main` branch
- the matching GitHub environment name
- ECR publishing permissions for the platform repositories
- optional `eks:DescribeCluster` permission for kubeconfig generation

The only wildcard permission is `ecr:GetAuthorizationToken`, which AWS requires to use resource `"*"`.

Phase 16 wires the optional dev role into the dev EKS cluster with an EKS access entry scoped to the `ai-platform-dev` namespace using the AWS-managed `AmazonEKSEditPolicy`. Phase 17 applies the same namespace-scoped pattern to staging and prod deploy roles. The deployment workflows therefore expect namespaces and runtime secrets to be bootstrapped before deploys are enabled.

## Managed Data Services

Phase 13 wires private managed data services into every environment.

RDS PostgreSQL defaults:

- private subnets only
- no public accessibility
- encrypted gp3 storage
- AWS-managed master password
- autoscaled storage ceiling per environment
- automated backups
- environment-specific backup retention of 1 day in dev, 7 days in staging, and 14 days in prod
- deletion protection enabled for staging and prod
- final snapshots enabled for staging and prod
- Multi-AZ enabled for staging and prod
- ingress restricted to the EKS cluster security group

ElastiCache Redis defaults:

- private subnets only
- encrypted at rest and in transit
- snapshot retention per environment
- snapshot retention of 1 day in dev, 7 days in staging, and 14 days in prod
- automatic failover and Multi-AZ enabled for staging and prod
- ingress restricted to the EKS cluster security group

Dev remains deliberately smaller:

- single-AZ database
- single Redis cache cluster
- shorter backup and snapshot retention
- deletion protection disabled for easier approved teardown

Applying these modules creates paid resources and remains an explicit approval gate.

See `docs/backup-restore.md` for RTO/RPO targets, database restore steps, Redis persistence decisions, and DR assumptions.
See `docs/cost-analysis.md` for environment cost estimates, right-sizing notes, optional budget alerts, and dev teardown guidance.
