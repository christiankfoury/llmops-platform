# Terraform

Phase 11 introduces the AWS foundation as Terraform code only. Do not run `terraform apply` or create cloud resources without explicit human approval.

## Scope

Current modules:

- `modules/network`: VPC, public subnets, private subnets, route tables, optional NAT gateway
- `modules/registry`: ECR repositories for API and web images with immutable tags and scan-on-push
- `modules/secrets`: AWS Secrets Manager placeholder secrets without secret values
- `modules/iam`: optional GitHub Actions OIDC role for future ECR publishing

Current environments:

- `environments/dev`
- `environments/staging`
- `environments/prod`

Later phases add EKS, RDS PostgreSQL, ElastiCache Redis, Kubernetes, Helm, deployment workflows, and stronger security controls.

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

## Environment Defaults

Dev is cost-conscious by default:

- two availability zones
- NAT gateway disabled
- shorter ECR image retention
- 7-day secret recovery window

Staging and prod are more production-like:

- staging uses two availability zones and NAT enabled
- prod uses three availability zones and NAT enabled
- longer ECR retention
- longer secret recovery windows

These defaults are code only. Applying them creates paid AWS resources and requires explicit approval.

## Secrets

The secrets module creates only secret containers/placeholders in AWS Secrets Manager. It does not create `aws_secretsmanager_secret_version` resources and does not store secret values in Terraform state.

Secret values must be written through an approved secure process outside this repository.

## IAM

The IAM module can create a GitHub Actions OIDC provider and ECR publish role, but it is disabled by default in every environment.

When enabled, the role is restricted to:

- this repository
- the `main` branch
- the matching GitHub environment name
- ECR publishing permissions for the platform repositories

The only wildcard permission is `ecr:GetAuthorizationToken`, which AWS requires to use resource `"*"`.
