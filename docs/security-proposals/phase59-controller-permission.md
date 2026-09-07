# Proposed ALB controller permission exception

Status: **Pending user approval. No scanner suppression is active.**

The remaining Phase 59 scan finding is `KSV-0056` on the `load-balancer-reconciler` Role. The local configured-manifest scan reports eight copies of the same capability because it validates base/dev/staging/prod and both bootstrap stages. All other rendered HIGH/CRITICAL findings were removed by implementation changes.

## Exact permission and purpose

Only ServiceAccount `kube-system/aws-load-balancer-controller` is bound to this Role, in `ai-platform-dev`, `ai-platform-staging` or `ai-platform-prod` within its own environment cluster:

```yaml
apiGroups: [networking.k8s.io]
resources: [ingresses]
verbs: [get, list, watch, patch, update]
```

The controller writes reconciliation finalizers on Ingress objects. Removing its write permission prevents normal reconciliation and finalizer cleanup. This is present in the pinned upstream [v3.5.0 RBAC](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/config/rbac/role.yaml); [Ingress finalizer handling](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/pkg/ingress/finalizer.go) calls the [Kubernetes finalizer manager](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/pkg/k8s/finalizer.go), which patches the object with optimistic locking.

The permission is intentionally powerful: a compromised controller could modify Ingress objects in its application namespace. The scanner correctly identifies that capability. This proposal accepts that bounded operational requirement; it does not claim the permission is risk-free or that a live deployment has been security-tested.

## Boundaries already implemented

- The app deployer cannot mutate Services, Ingress or NetworkPolicies; these belong to the bootstrap network release.
- The ALB controller's cluster-wide permissions are read-only discovery. Network mutation is limited to Ingress objects in its application namespace. It cannot mutate Services, endpoints, NetworkPolicies or Secrets.
- NLB/Service, Gateway and Global Accelerator controllers are disabled for this ALB-only platform. A dedicated IRSA role and exact ServiceAccount trust remain in place.
- External Secrets uses separate namespace-scoped controllers, reader identities and v1 SecretStores. There is no cluster-wide Secret access or runtime webhook-management permission.
- Controller configuration is pinned, checksum verified and rendered for every environment. Pods use explicit security contexts. Every positive object has its own scan file.
- The RBAC validator rejects any other network-writing Role, any cluster-wide write grant, and any expansion of this Ingress rule. Application and migration boundary checks remain mandatory.

## Concrete proposed change

[phase59-trivyignore.proposed.yaml](phase59-trivyignore.proposed.yaml) proposes one finding ID, a bounded list of exact source/resource paths, an explanation and expiration on **2026-10-07**. It is not at a default ignore location and no workflow references it. There are no vulnerability or secret exceptions.

If approved, activate explicit ignore-file selection only for the repository/configured-infrastructure scans, test that the expected finding is filtered and that an unrelated Role or changed permission still fails, then rerun full CI. Every other security finding remains blocking. Expiration or a changed controller permission requires a fresh review. A blanket `KSV-0056` exception, scan removal, lower severity threshold, or `continue-on-error` is not proposed. [Trivy's scoped/expiring ignore-file format](https://trivy.dev/docs/latest/configuration/filtering/#trivyignoreyaml).

Reviewed source: `infra/bootstrap/ai-platform-bootstrap/templates/load-balancer-rbac.yaml`.
Canonical LF SHA-256: `8ad34b68a95cdd63a4cf6b83685c2f1be0f2021a9d7f74823b02053e538853d2`.

## Why approval is required

[AGENTS.md](../../AGENTS.md:228) lists “Disabling security checks” among actions requiring approval. I am treating suppression of this specific blocking check as covered by that gate, even though it would be limited to the documented controller capability. Implementation fixes, schema/plan validation, commits and pushed reviews continue to be authorized; enabling this exception requires the user's decision.

This approval would authorize only the scanner exception. It would not authorize AWS apply/resources, credentials, production deployment, DNS, public repository visibility or any other release gate.
