# Phase 59 Review

## Summary

AWS bootstrap is separated from namespace-scoped Java application releases. Pinned offline validation now checks every Terraform root, both bootstrap graph stages, Kubernetes built-ins and controller CRDs.

## Scope Check

- In scope: Terraform planning correctness, explicit EKS add-ons/policy enforcement, authenticated private data, migration registry/identity/namespace prerequisites, reproducible all-environment validation and bootstrap documentation.
- Out of scope avoided: real AWS calls/resources, paid deployment, secret creation/rotation, DNS, application features, Java supply-chain eligibility and immutable promotion execution (Phases 60/61), running monitoring (62).

## Files Changed

- Terraform environment roots/provider locks, cluster/add-ons/controllers, IAM, Redis, security-group iteration and split secret-reader modules.
- Bootstrap chart/controller values; namespace-only app chart/raw overlays; separate migration chart.
- Pinned tools/charts/schemas/public trust/provenance, validation scripts, CI, bootstrap/deployment/cutover docs and phase progress.

## Validation

- Command: pinned Terraform `fmt -check`, backend-disabled `init -lockfile=readonly`, `validate`, mocked `test` for dev/staging/prod.
- Result: all passed, six mock plans with no AWS calls. Computed security-group keys and secret-reader counts are plan-safe. Both Windows/Linux provider package hashes are locked.
- Command: `python scripts/validate_java_manifests.py`; `python scripts/validate_aws_manifests.py`.
- Result: runtime checks and 506 schema-validated resource instances passed, zero skipped. Three deliberately invalid resources failed as required. Duplicate YAML and CRD property-name conversion regressions passed. Terraform/bootstrap default CIDRs agree.
- Command: Ruff for changed scripts, CI YAML parsing and `git diff --check`.
- Result: passed. No application runtime/Docker source changes required repeated local Java or image tests; the full pushed CI remains required.

## Security Review

- Secrets: no real values; public RDS certificates only. Redis token is ephemeral/write-only. Owner credentials are outside app namespace and runtime reader permissions.
- Auth: GitHub subjects require exact app/migration environments and STS audience; no implicit EKS creator-admin access.
- IAM/RBAC: dedicated CNI/CSI/LB/secret-reader roles; cluster-bootstrap principal separated from app and migration Kubernetes groups. ESO now uses separate namespace-scoped controllers and stores; each may request tokens only for its own named reader SA. Its runtime has no ClusterRole or webhook-management permissions. The ALB controller has read-only cluster discovery and an app-namespace Ingress-only reconciler. Upstream LB policy wildcard statements are preserved with provenance and tag conditions.
- Network: private EKS/data defaults; strict CNI bootstrap sequence and policies; metrics-server ports support HPA. NAT egress and its cost/failure dependency are explicit.
- Supply chain: checksummed tool archives, signed provider locks, pinned charts/schema commit/public CA/policy with byte-stable Git attributes. Missing schemas fail.

## Reliability Review

- Health checks: existing Java checks unchanged; managed DNS/CSI/metrics and controller readiness must pass the later live bootstrap checks.
- Rollback: application releases do not own cluster resources or owner Jobs. Existing Helm ownership/state changes require a reviewed transfer; no blind upgrade/deletion.
- Failure handling: default-disabled second add-on stage avoids strict-CNI bootstrap ordering deadlock. Invalid schema/config fails offline; no AWS call is needed.

## Observability Review

- Logs: EKS control-plane logging retained; no secret dumps in validation.
- Metrics: private Java scrape policy retained; required metrics-server defined for HPA.
- Traces: Java tracing unaffected.
- Dashboards: running monitoring stack and selectors remain Phase 62.

## Risks / Follow-ups

- Regional add-on build IDs and engine availability must be verified at Phase 65 preflight; test build values are synthetic. No live capacity, admission, IAM or network enforcement evidence claimed.
- One NAT is currently an AZ dependency and recurring cost; finalize budget/topology in Phases 63/65. Private runner/DNS and account-wide state/OIDC prerequisites are documented, not provisioned.
- Cluster CEL/admission and actual managed add-on labels/ports require gated live checks. Current resources target fresh clusters; old ownership or Terraform state needs a reviewed handoff.

## Post-Commit Review

- Pushed commit: `dd125e66df161df7be2c768ed04a2dd705c3a372`.
- Top findings: CI 34091679445 passed infrastructure checks but flagged app-deployer network mutations (KSV-0056) and upstream ESO archive default permissions/security context. First fix transfers Services/Ingress/NetworkPolicy ownership to a separate bootstrap network release and makes these objects read-only to the app deployer; ESO broad privileges are removed by separate namespace-scoped reconcilers and v1 stores. Configured-source scans now cover the actual deployment; the only remaining finding is KSV-0056 on the ALB controller's required Ingress finalizer permission.
- Fix commits: `a1e48c541119c99127fc28d60defe7ade36d2248` removes app-deployer network mutations. `5ab54f3d33be4bfa3c4400eed133d37e2a0d54e7` fixes the network chart's namespace fallback and adds cross-release namespace checks. `9133c2d9ba94dce41464ea1241ec8ecda9e8432c` scopes controllers, verifies configured deployment scans and records the inactive permission proposal. Its post-push review identified shared default ESO leader-election IDs; a separate fix assigns each reconciler its own ID and verifies rendered arguments. No scan suppression has been enabled; the sole remaining capability exception is documented for approval.

## Next Phase

- Phase 60: Java supply chain and CI release eligibility, after the required review/fix loop.
