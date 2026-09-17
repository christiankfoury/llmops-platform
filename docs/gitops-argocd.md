# GitOps with Argo CD

## Purpose

This document explains the optional Argo CD GitOps path for the LLMOps Platform.

GitHub Actions remains the default CI/CD path. Argo CD is an additional portfolio-grade deployment option that can continuously reconcile the same Helm chart from Git when an operator intentionally enables it.

## Repository Layout

```text
infra/gitops/argocd/
  README.md
  projects/
    ai-platform-project.yaml
  applications/
    ai-platform-dev.yaml
    ai-platform-staging.yaml
    ai-platform-prod.yaml
```

Each Argo CD Application points to:

- repo: `https://github.com/christiankfoury/llmops-platform.git`
- revision: `main`
- chart path: `infra/helm/ai-platform`
- values file:
  - dev: `values-dev.yaml`
  - staging: `values-staging.yaml`
  - prod: `values-prod.yaml`

## Install Notes

Installing Argo CD changes a real cluster and requires approval.

Reference install flow after approval:

```bash
kubectl create namespace argocd
kubectl apply --namespace argocd --filename https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl rollout status deployment/argocd-server --namespace argocd --timeout=10m
```

Bootstrap the platform project and applications:

```bash
kubectl apply --filename infra/gitops/argocd/projects/ai-platform-project.yaml
kubectl apply --filename infra/gitops/argocd/applications/ai-platform-dev.yaml
kubectl apply --filename infra/gitops/argocd/applications/ai-platform-staging.yaml
kubectl apply --filename infra/gitops/argocd/applications/ai-platform-prod.yaml
```

Do not run these commands from Codex without explicit human approval.

## Sync Strategy

Dev:

- Automated sync is enabled for self-healing.
- Pruning is disabled to avoid deleting resources during portfolio experimentation.
- Use this only when the GitHub Actions dev deploy workflow is disabled for the same namespace.

Staging:

- Manual sync only.
- Promotion should happen through a reviewed Git change, then an operator manually syncs the staging Application.
- This keeps staging aligned with the existing manual release validation story.

Prod:

- Manual sync only.
- Production sync requires the same approval discipline as the existing production GitHub Environment gate.
- Do not enable automated production sync unless a future phase adds a clear approval and rollback model.

## Promotion Model

The current GitHub Actions path builds immutable images and deploys them with Helm overrides.

The GitOps path should promote images by Git:

1. Build and scan images in CI.
2. Push immutable image tags to ECR.
3. Update the relevant Helm values file or a dedicated GitOps values overlay with the immutable tag.
4. Review and merge the Git change.
5. Let dev auto-sync, or manually sync staging/prod.
6. Verify rollout, smoke tests, metrics, logs, and traces.

Do not let GitHub Actions and Argo CD both continuously write the same Helm release in the same namespace. Pick one controller per environment.

## Rollback

GitOps rollback options:

- revert the Git commit that changed image tags or values
- sync the previous healthy Git revision
- use the existing Helm rollback workflow only if Argo CD is paused or the Application is temporarily not reconciling

After rollback, verify:

- API readiness
- web health
- recent 5xx rate
- gateway p95 latency
- estimated cost and token metrics
- request-correlated logs and traces

## Secrets and Access

Argo CD manifests do not contain secret values.

Runtime values still flow through:

- AWS Secrets Manager
- External Secrets Operator
- `ai-platform-runtime-secrets`

Argo CD needs read access to this public repository and Kubernetes permissions scoped to the target platform namespaces. Cluster-admin installation is an approval-gated bootstrap action, not normal deployment work.

The included AppProject allows only the cluster-scoped `Namespace` and `ClusterSecretStore` resources plus the namespaced resource kinds rendered by the Helm chart. Avoid replacing this with wildcard resource permissions unless a future chart change makes the extra permission necessary and reviewed.

## Validation

Safe local validation:

```bash
helm lint infra/helm/ai-platform
helm template ai-platform-dev infra/helm/ai-platform -f infra/helm/ai-platform/values-dev.yaml --namespace ai-platform-dev
helm template ai-platform-staging infra/helm/ai-platform -f infra/helm/ai-platform/values-staging.yaml --namespace ai-platform-staging
helm template ai-platform-prod infra/helm/ai-platform -f infra/helm/ai-platform/values-prod.yaml --namespace ai-platform-prod
```

Manifest sanity checks:

```bash
rg -n "kind: Application|path: infra/helm/ai-platform|values-dev.yaml|values-staging.yaml|values-prod.yaml|automated|manual" infra/gitops/argocd docs/gitops-argocd.md
```

## Scope Boundary

Phase 29 adds optional GitOps manifests and documentation only. It does not install Argo CD, mutate a cluster, replace GitHub Actions workflows, or enable production auto-sync.
