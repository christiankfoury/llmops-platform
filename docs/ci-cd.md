# CI/CD

This document explains the GitHub Actions workflows in this repository, starting with the main CI workflow:

```text
.github/workflows/ci.yml
```

The short version:

```text
git push / pull request
  -> GitHub Actions starts temporary Ubuntu runners
  -> backend, frontend, image, dependency, repository, and infrastructure checks run
  -> CI passes or fails before deployment workflows should be trusted
```

CI runs on GitHub-hosted machines, not on the local developer machine. Local Docker Compose is for running the application locally; GitHub Actions is for proving that committed code builds, tests, and scans cleanly in a fresh environment.

## Useful Links

GitHub Actions:

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [GitHub-hosted runners](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners)
- [Service containers](https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

Actions used by this repository:

- [actions/checkout](https://github.com/actions/checkout)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/setup-node](https://github.com/actions/setup-node)
- [docker/setup-buildx-action](https://github.com/docker/setup-buildx-action)
- [docker/build-push-action](https://github.com/docker/build-push-action)
- [Build and push Docker images marketplace page](https://github.com/marketplace/actions/build-and-push-docker-images)
- [aquasecurity/trivy-action](https://github.com/aquasecurity/trivy-action)
- [hashicorp/setup-terraform](https://github.com/hashicorp/setup-terraform)

Tools run inside CI:

- [Ruff](https://docs.astral.sh/ruff/)
- [pytest](https://docs.pytest.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [npm audit](https://docs.npmjs.com/cli/commands/npm-audit)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Trivy](https://trivy.dev/)
- [Helm](https://helm.sh/docs/)
- [Terraform](https://developer.hashicorp.com/terraform/docs)

## CI Versus Local Development

Local development:

```text
docker compose up --build
```

This starts the API, web app, PostgreSQL, and Redis on the developer machine.

CI:

```text
GitHub Actions runner
```

This checks out the repository into a clean temporary machine and runs validation commands. It does not use the local Docker Compose stack and does not use local files that were not committed.

That difference is important:

```text
Local can pass because your machine has state.
CI proves the repo works from a clean checkout.
```

## When CI Runs

The CI workflow runs on:

```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
```

That means CI runs when:

- code is pushed to `main`
- a pull request targets `main`

This keeps the main branch and proposed changes under the same quality gate.

## Permissions

The workflow uses:

```yaml
permissions:
  contents: read
```

That gives the workflow read access to repository contents. The CI workflow does not need write access because it does not publish releases, push images, create pull requests, or mutate infrastructure.

Deployment workflows need broader cloud permissions through GitHub OIDC, but CI intentionally stays read-only.

## Backend Job

The backend job validates the FastAPI application:

```text
Backend lint and tests
```

It runs on:

```yaml
runs-on: ubuntu-latest
```

That tells GitHub to start a temporary Ubuntu runner.

### PostgreSQL Service

The backend job starts a temporary PostgreSQL container:

```yaml
services:
  postgres:
    image: postgres:16-alpine
```

This database exists only for the job. It is not the local database and not a cloud database.

The service maps:

```yaml
ports:
  - 55432:5432
```

So backend commands running on the GitHub runner can connect to:

```text
localhost:55432
```

while the Postgres container itself listens on:

```text
5432
```

### Backend Environment Variables

The backend job sets:

```yaml
env:
  DATABASE_URL: postgresql+psycopg://ai_platform:local_dev_password@localhost:55432/ai_platform
  REDIS_URL: redis://localhost:6379/0
  API_CORS_ORIGINS: http://localhost:3000
```

These variables configure the FastAPI application during CI.

The important one is `DATABASE_URL`: it points the app and Alembic migrations at the temporary PostgreSQL service container.

`REDIS_URL` is present because the app config expects Redis configuration. The current CI backend tests do not require a live Redis service for the normal gateway test path. If future tests need Redis-backed behavior, add a Redis service container and point `REDIS_URL` at it.

### Backend Steps

The backend job does this:

```text
checkout repo
setup Python
install backend dependencies
run Ruff lint
run Ruff format check
run Alembic migrations
run pytest
```

The migration step matters because it catches schema drift:

```text
SQLAlchemy models changed, but migration did not
```

or:

```text
migration is invalid against a fresh database
```

That kind of failure is easier to catch in CI than after deployment.

## Frontend Job

The frontend job validates the Next.js dashboard:

```text
Frontend lint, typecheck, tests, and audit
```

It runs all commands from:

```text
apps/web
```

The job does:

```text
checkout repo
setup Node.js
npm ci
npm run lint
npm run typecheck
npm run test
npm audit --audit-level=high
```

`npm ci` is used instead of `npm install` because CI should install exactly what is in `package-lock.json`.

The frontend checks answer:

```text
Does the dashboard lint?
Does TypeScript compile?
Do component tests pass?
Do high/critical npm audit findings block the build?
```

## Production Image Build And Scan Job

The Docker job validates production container images:

```text
Production image build and scan
```

This job is not using `Dockerfile.dev`. It builds production images:

```text
apps/api/Dockerfile
apps/web/Dockerfile
```

The important action is:

```yaml
uses: docker/build-push-action@v7
```

That comes from:

```text
https://github.com/docker/build-push-action
```

The pattern is:

```text
uses: owner/repository@version
```

So:

```text
docker/build-push-action@v7
```

means:

```text
owner = docker
repository = build-push-action
version = v7
```

The CI workflow uses:

```yaml
load: true
push: false
```

That means:

```text
Build the image and load it into the CI runner's Docker engine.
Do not push it to a registry.
```

The images are tagged locally inside CI:

```text
production-ai-platform-api:ci
production-ai-platform-web:ci
```

Then Trivy scans those images:

```yaml
severity: HIGH,CRITICAL
exit-code: "1"
ignore-unfixed: true
```

That means high or critical findings fail the job, while unfixed findings without available patches are ignored.

This job answers:

```text
Can the production images build?
Do the production images have blocking high/critical known vulnerabilities?
```

## Python Dependency Scan Job

The Python dependency scan uses:

```text
pip-audit
```

It audits:

```text
apps/api/requirements.prod.txt
```

That is intentionally the production dependency file, not the development dependency file.

The command is:

```bash
python -m pip_audit -r apps/api/requirements.prod.txt --strict
```

`--strict` means audit errors are treated as failures. This prevents the scan from silently passing when the audit itself cannot complete correctly.

This job answers:

```text
Do production Python dependencies contain blocking known vulnerabilities?
```

## Repository Vulnerability Scan Job

The repository scan uses Trivy in filesystem mode:

```yaml
scan-type: fs
scan-ref: .
scanners: vuln,config,secret
```

It scans more than just Python or Node dependencies:

```text
vulnerabilities
infrastructure/config issues
secret patterns
```

This is useful for a cloud portfolio project because risk can appear in Terraform, Kubernetes, Helm, Dockerfiles, or accidentally committed secrets.

This job answers:

```text
Does the repository contain high/critical dependency, config, or secret findings?
```

## Infrastructure Static Checks Job

The infrastructure job runs checks only:

```text
Infrastructure static checks
```

It does not create AWS resources.

It runs Terraform formatting:

```bash
terraform fmt -check -recursive infra/terraform
```

and Helm lint:

```bash
helm lint infra/helm/ai-platform
```

These are safe checks. They validate code and chart shape, but they do not run:

```text
terraform apply
helm upgrade
kubectl apply
```

That distinction matters because applying infrastructure can create real cloud cost or mutate environments. This repository keeps those actions in approved deployment workflows or explicit human-gated operations.

## Why There Are Separate Jobs

The workflow could be one large job, but separate jobs make failures easier to understand.

For example:

```text
Backend lint and tests failed
```

is different from:

```text
Production image scan failed
```

Separate jobs also let GitHub run checks in parallel, so the total CI time is shorter.

## What CI Does Not Do

The main CI workflow does not:

- deploy to AWS
- create EKS clusters
- apply Terraform
- push images to ECR
- rotate secrets
- run production migrations
- change DNS or TLS

Those actions are intentionally separated because they can create cost, downtime, or production impact.

## How This Fits The Project

The application proves the gateway and dashboard work.

CI proves the project is shippable:

```text
backend quality
frontend quality
production image builds
supply-chain checks
repository/config/secret scans
infrastructure static checks
```

That is why CI matters in this project. It is part of the production story, not just a test runner.
