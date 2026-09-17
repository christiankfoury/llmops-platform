# Argo CD GitOps

This directory contains optional Argo CD manifests for deploying the LLMOps Platform Helm chart.

It is not the default deployment path. GitHub Actions remains the primary CI/CD and release workflow unless an operator intentionally chooses the GitOps path for a namespace.

Manifests:

- `projects/ai-platform-project.yaml`: Argo CD project scoped to this repository and the platform namespaces.
- `applications/ai-platform-dev.yaml`: Helm-based dev application with automated self-heal enabled and pruning disabled.
- `applications/ai-platform-staging.yaml`: Helm-based staging application with manual sync.
- `applications/ai-platform-prod.yaml`: Helm-based prod application with manual sync.

The project manifest enumerates the Kubernetes resource kinds rendered by the chart instead of allowing all namespaced resources.

Before applying these manifests:

- Install Argo CD into an approved cluster.
- Bootstrap the target namespaces, runtime secrets, External Secrets permissions, ingress dependencies, DNS, and TLS.
- Replace placeholder image repositories and tags in the Helm values or promote immutable image tags through an approved Git change.
- Disable the overlapping GitHub Actions deploy workflow for any namespace Argo CD controls, or use Argo CD only as a read-only demo.

Safe validation:

```bash
helm lint infra/helm/ai-platform
helm template ai-platform-dev infra/helm/ai-platform -f infra/helm/ai-platform/values-dev.yaml --namespace ai-platform-dev
helm template ai-platform-staging infra/helm/ai-platform -f infra/helm/ai-platform/values-staging.yaml --namespace ai-platform-staging
helm template ai-platform-prod infra/helm/ai-platform -f infra/helm/ai-platform/values-prod.yaml --namespace ai-platform-prod
```

Applying Argo CD manifests to a real cluster changes deployment control and requires explicit approval.
