# Pinned offline validation inputs

`toolchain.json` pins Terraform 1.16.1, Helm 3.21.4 and kubeconform 0.8.0 archives for Linux/Windows x86_64. `scripts/install_validation_tools.py` verifies SHA-256 before extracting only the named binary into ignored `.maven-cache/tools/pinned`. Helm stays on the maintained 3.x line for the existing chart/release interface.

`charts.json` records exact official chart archives for External Secrets 2.10.0 and AWS Load Balancer Controller 3.5.0. Their rendered controller resources and CRDs are schema checked, including nested `List` items. Archives include upstream notices; vendoring does not relicense them. Bootstrap controllers are separately privileged releases, never application chart dependencies.

`schemas/kubernetes/sources.json` pins 21 Kubernetes 1.36.0 standalone strict schemas to one upstream commit, with per-file checksums and the upstream license. That generated registry omits CustomResourceDefinition itself. `schemas/crd-source.json` therefore pins the official Kubernetes 1.36.0 apiextensions OpenAPI document. The validator converts schema-valued keywords and preserves typed maps, nullable fields and explicit unknown-field islands; it never interprets field names such as `nullable` as schema keywords. Custom resource schemas come from the exact rendered, pinned controller CRDs. Kubernetes CEL validation and admission behavior still require the gated cluster acceptance checks.

All source hashes are verified before rendering/validation. Local generated schemas and controller TLS fixtures stay under ignored `.maven-cache`. No network schema fallback or missing-schema exemption is used. Negative probes must reject an invalid built-in type, unknown ExternalSecret property and entirely unregistered resource kind. Git attributes preserve third-party bytes across Windows/Linux checkout.

The public RDS trust bundle and upstream load-balancer IAM policy have separate adjacent `sources.json` records. The IAM policy retains upstream tag-scoped mutation and required wildcard discovery/create permissions; only the exact controller ServiceAccount can assume its role. The RDS bundle contains public certificates only.

Update inputs intentionally: verify an upstream release and checksum, update its source record and bytes together, render every environment, run `python scripts/validate_aws_manifests.py`, review the diff and pass CI. No unreviewed latest URL is used at validation time.
