# Deployment

## Environments

The project targets four environments:

- local
- dev
- staging
- prod

## Local deployment

Implemented local stack:

```text
Docker Compose:
- API
- Web
- PostgreSQL
- Redis
```

Start the full stack:

```bash
docker compose up --build
```

The same command is available as:

```bash
make local-up
```

Local service URLs:

- Web dashboard: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/health/ready`
- PostgreSQL host port: `55432`
- Redis host port: `56379`

The web dashboard reads the API directly through `NEXT_PUBLIC_API_BASE_URL` and renders usage, recent requests, failures, prompt versions, and model routes.

Stop containers:

```bash
make local-down
```

Run database migrations and seed local development data after the stack is running:

```bash
make api-migrate
make api-seed
```

## Production image builds

Phase 9 adds production Dockerfiles for the API and web dashboard while keeping the development Dockerfiles used by Docker Compose.

Build both production images:

```bash
make docker-build-prod
```

Equivalent direct commands:

```bash
docker build -f apps/api/Dockerfile -t production-ai-platform-api:prod apps/api
docker build -f apps/web/Dockerfile -t production-ai-platform-web:prod apps/web
```

The API production image:

- installs runtime dependencies from `requirements.prod.txt`
- excludes test and formatting tools from the runtime dependency set
- runs as non-root user `10001`
- exposes port `8000`
- defines a container health check against `/health/live`
- reads `ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`, and `API_CORS_ORIGINS` from environment variables

The web production image:

- uses a multi-stage Next.js standalone build
- runs as non-root user `10001`
- exposes port `3000`
- defines a container health check against `/`
- reads `API_BASE_URL` or `NEXT_PUBLIC_API_BASE_URL` at runtime through `/api/runtime-config`

Local production-image smoke test:

```bash
docker run --rm -p 18000:8000 production-ai-platform-api:prod
docker run --rm -p 13000:3000 -e API_BASE_URL=http://host.docker.internal:8000 production-ai-platform-web:prod
```

Those commands start containers locally only. Cloud registry publishing and Kubernetes deployment are later-phase work.

Smoke-test the local gateway with the seeded placeholder key:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"hello from local development"}'
```

The local seed key is intentionally non-secret placeholder data and is stored as a hash.

The mock provider supports local failure-path checks:

- `"[simulate_failure]"` returns HTTP 502 and records `provider_error`.
- `"[simulate_timeout]"` returns HTTP 504 and records `provider_timeout`.

Check aggregate usage after sending gateway requests:

```bash
curl http://localhost:8000/v1/usage/summary
```

Inspect local operator configuration:

```bash
curl http://localhost:8000/v1/admin/prompt-versions
curl http://localhost:8000/v1/admin/model-routes
```

Admin create/update calls accept `X-Actor-ID` and write audit logs. These endpoints are intentionally not production-hardened yet; admin authentication and stronger access controls are later-phase work.

Local environment examples live in:

- `.env.example`
- `apps/api/.env.example`
- `apps/web/.env.example`

These files use placeholder development values only. Real provider keys, cloud account IDs, and production secrets must not be committed.

## Dev deployment

Phase 16 adds `.github/workflows/deploy-dev.yml` for the dev release path.

The workflow can run in two ways:

- automatically on pushes to `main` when both repository variables are set to `true`:
  - `ENABLE_DEV_AUTO_DEPLOY`
  - `DEV_DEPLOY_APPROVED`
- manually through `workflow_dispatch`, with an optional immutable image tag override

The enablement variables intentionally default to absent/false. This lets the workflow be committed safely without mutating a real AWS account until the dev environment has been approved and bootstrapped.

Dev workflow steps:

1. Resolve required repository variables and fail fast if any are missing.
2. Assume the dev GitHub Actions IAM role through OIDC.
3. Build API and web production images.
4. Push images to ECR with the commit SHA as the immutable image tag.
5. Update kubeconfig for the dev EKS cluster.
6. Run `helm upgrade --install` for the `ai-platform-dev` release.
7. Wait for API and web deployment rollouts.
8. Run smoke tests against API readiness and the web dashboard URL.

Required GitHub repository variables:

| Variable | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | AWS account that owns the dev ECR repositories. |
| `AWS_REGION` | AWS region for ECR and EKS. |
| `AWS_DEV_DEPLOY_ROLE_ARN` | OIDC role assumed by GitHub Actions for dev deploys. |
| `DEV_EKS_CLUSTER_NAME` | Dev EKS cluster name, such as `production-ai-platform-dev-eks`. |
| `DEV_API_HOST` | Ingress host for the dev API. |
| `DEV_WEB_HOST` | Ingress host for the dev web dashboard. |
| `DEV_API_BASE_URL` | Public base URL used for API smoke tests and web runtime config. |
| `DEV_WEB_BASE_URL` | Public base URL used for web smoke tests and API CORS config. |

Optional GitHub repository variables:

| Variable | Default | Purpose |
|---|---|---|
| `DEV_NAMESPACE` | `ai-platform-dev` | Kubernetes namespace for the dev release. |
| `DEV_API_ECR_REPOSITORY` | `production-ai-platform-dev/api` | Dev API ECR repository name. |
| `DEV_WEB_ECR_REPOSITORY` | `production-ai-platform-dev/web` | Dev web ECR repository name. |

Dev bootstrap prerequisites before enabling automatic deploys:

- Terraform dev infrastructure has been applied through an approved human gate.
- The optional dev GitHub Actions role is enabled with `create_github_actions_role = true`.
- The `ai-platform-dev` namespace exists in the dev cluster.
- The runtime secret reference expected by the chart exists in the namespace:
  - Secret name: `ai-platform-runtime-secrets`
  - Keys: `database-url`, `redis-url`
- DNS/ingress routes resolve for `DEV_API_HOST` and `DEV_WEB_HOST`.

The Phase 16 workflow overrides `namespace.create=false` during Helm deploys so the GitHub deploy role can be scoped to edit the dev namespace rather than administer the whole cluster. Namespace and secret bootstrap remain explicit setup steps because they can affect real infrastructure and secrets.

No AWS keys, kubeconfigs, database URLs, Redis URLs, or provider credentials are committed. The workflow uses GitHub OIDC and repository/environment variables only.

Terraform foundation code for dev, staging, and prod lives under `infra/terraform/environments`. Phase 11 supports safe local `fmt`, `init -backend=false`, and `validate` checks only. Creating AWS resources with `terraform apply` is an explicit approval gate.

See `docs/terraform.md` for backend configuration, AWS credential expectations, and validation commands.

Phase 12 adds EKS Terraform code and Kubernetes provider wiring. It remains code-only until an explicit approval gate allows AWS resource creation.

Phase 13 adds managed PostgreSQL and Redis Terraform code. These resources are private, encrypted, and backed up by default, but they are still not created until an approved `terraform apply`.

## Kubernetes manifests

Phase 14 adds raw Kubernetes manifests under `infra/k8s`.

Render the base manifests:

```bash
kubectl kustomize infra/k8s/base
```

Render environment overlays:

```bash
kubectl kustomize infra/k8s/overlays/dev
kubectl kustomize infra/k8s/overlays/staging
kubectl kustomize infra/k8s/overlays/prod
```

The manifests include:

- namespace per environment
- API and web service accounts
- API and web ConfigMaps
- API and web Deployments
- API and web ClusterIP Services
- ALB-oriented Ingress
- liveness and readiness probes
- resource requests and limits
- non-root pod and container security contexts
- secret references for `DATABASE_URL` and `REDIS_URL`

The referenced `ai-platform-runtime-secrets` Secret is intentionally not committed. Later External Secrets work will bind AWS Secrets Manager values into Kubernetes without plaintext manifests.

These manifests are raw Kubernetes foundations. Helm packaging, release values, External Secrets, HPA, PDB, and NetworkPolicies are later phases.

## Helm chart

Phase 15 adds the Helm chart at `infra/helm/ai-platform`.

Lint the chart:

```bash
helm lint infra/helm/ai-platform
```

Render environment releases:

```bash
helm template ai-platform-dev infra/helm/ai-platform \
  -f infra/helm/ai-platform/values-dev.yaml \
  --namespace ai-platform-dev

helm template ai-platform-staging infra/helm/ai-platform \
  -f infra/helm/ai-platform/values-staging.yaml \
  --namespace ai-platform-staging

helm template ai-platform-prod infra/helm/ai-platform \
  -f infra/helm/ai-platform/values-prod.yaml \
  --namespace ai-platform-prod
```

The chart packages:

- namespace creation toggle
- service accounts
- API and web ConfigMaps
- API and web Deployments
- API and web Services
- ALB-oriented Ingress
- optional API and web HPAs
- runtime Secret references for database and Redis connection strings

The Helm chart is the release artifact for deployment workflows. Phase 16 overrides dev image repositories, image tags, ingress hosts, CORS origins, and web API base URL at deploy time from GitHub repository variables.

## Staging deployment

Phase 17 adds `.github/workflows/deploy-staging.yml` for manual staging promotion.

Staging workflow:

1. Operator starts `Deploy Staging` with an optional immutable image tag and release notes.
2. Workflow assumes `AWS_STAGING_DEPLOY_ROLE_ARN` through GitHub OIDC.
3. API and web images are built from the selected ref and pushed to staging ECR using the commit SHA or supplied immutable tag.
4. Helm upgrades the `ai-platform-staging` release with `values-staging.yaml`.
5. API and web rollouts are checked.
6. API readiness and web dashboard smoke tests run.
7. A release summary is written to the GitHub Actions job summary.

Required staging repository variables:

| Variable | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | AWS account that owns staging ECR and EKS. |
| `AWS_REGION` | AWS region for staging ECR and EKS. |
| `AWS_STAGING_DEPLOY_ROLE_ARN` | OIDC role assumed by GitHub Actions for staging deploys. |
| `STAGING_EKS_CLUSTER_NAME` | Staging EKS cluster name. |
| `STAGING_API_HOST` | Ingress host for the staging API. |
| `STAGING_WEB_HOST` | Ingress host for the staging web dashboard. |
| `STAGING_API_BASE_URL` | Public base URL used for API smoke tests and web runtime config. |
| `STAGING_WEB_BASE_URL` | Public base URL used for web smoke tests and API CORS config. |

Optional staging repository variables:

| Variable | Default |
|---|---|
| `STAGING_NAMESPACE` | `ai-platform-staging` |
| `STAGING_API_ECR_REPOSITORY` | `production-ai-platform-staging/api` |
| `STAGING_WEB_ECR_REPOSITORY` | `production-ai-platform-staging/web` |

## Production deployment

Phase 17 adds `.github/workflows/deploy-prod.yml` for approved production releases.

Production workflow:

1. Operator starts `Deploy Prod` manually.
2. Operator supplies release notes and types `deploy-prod` in the confirmation input.
3. GitHub waits for the protected `prod` Environment approval before running deployment steps.
4. Workflow assumes `AWS_PROD_DEPLOY_ROLE_ARN` through GitHub OIDC.
5. API and web images are built from the selected ref and pushed to prod ECR using the commit SHA or supplied immutable tag.
6. Helm upgrades the `ai-platform-prod` release with `values-prod.yaml`.
7. API and web rollouts are checked with longer production timeouts.
8. API readiness and web dashboard smoke tests run.
9. A production release summary is written to the GitHub Actions job summary.

Required production repository variables:

| Variable | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | AWS account that owns prod ECR and EKS. |
| `AWS_REGION` | AWS region for prod ECR and EKS. |
| `AWS_PROD_DEPLOY_ROLE_ARN` | OIDC role assumed by GitHub Actions for prod deploys. |
| `PROD_EKS_CLUSTER_NAME` | Production EKS cluster name. |
| `PROD_API_HOST` | Ingress host for the production API. |
| `PROD_WEB_HOST` | Ingress host for the production web dashboard. |
| `PROD_API_BASE_URL` | Public base URL used for API smoke tests and web runtime config. |
| `PROD_WEB_BASE_URL` | Public base URL used for web smoke tests and API CORS config. |

Optional production repository variables:

| Variable | Default |
|---|---|
| `PROD_NAMESPACE` | `ai-platform-prod` |
| `PROD_API_ECR_REPOSITORY` | `production-ai-platform-prod/api` |
| `PROD_WEB_ECR_REPOSITORY` | `production-ai-platform-prod/web` |

Production GitHub Environment requirements:

- Create a GitHub Environment named `prod`.
- Add required reviewers for approval.
- Keep production variables scoped to the repository or environment according to the team's access model.
- Do not store static AWS keys; use the OIDC role only.

Promotion release notes template:

```text
Summary:
- What changed:
- Why it is safe:

Validation:
- CI run:
- Staging smoke test:
- Dashboard/log check:

Risk:
- Known risk:
- Rollback plan:
```

Staging and production bootstrap prerequisites:

- Terraform for the target environment has been applied through an approved human gate.
- The optional GitHub Actions role is enabled with `create_github_actions_role = true`.
- The target namespace exists before deploy:
  - staging: `ai-platform-staging`
  - prod: `ai-platform-prod`
- The runtime secret reference expected by the chart exists in the namespace:
  - Secret name: `ai-platform-runtime-secrets`
  - Keys: `database-url`, `redis-url`
- DNS/ingress routes resolve for the target API and web hosts.

The staging and production workflows override `namespace.create=false` during Helm deploys so deploy roles can be namespace-scoped. Namespace creation, runtime secret wiring, DNS/TLS, and infrastructure changes remain explicit approved operations outside these workflows.

## Rollback

Rollback is handled through Helm release history and a dedicated GitHub Actions rollback workflow.

See `docs/runbook.md` and `docs/incident-response.md`.
