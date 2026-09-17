# Immutable Java releases — Phase 61

Status: OCI export/copy compatibility passed in CI 34149204882 on 7aac16a before promotion workflow adoption. Phase 61 validation completed on 35719e2 in CI 34151436779 and read-only preflight 34151984454. Manual preflight is read-only; cloud execution remains hard-held. The [release runbook](immutable-release-runbook.md) defines the implemented procedure and remaining approval gates.

## Build and artifact ownership

Each CI image build produces a local Docker image for the existing runtime/TLS tests and scans, plus an OCI archive from the same build. Buildx 0.37.0 supports [multiple exporters](https://docs.docker.com/build/exporters/#multiple-exporters). The archive verifier checks every descriptor/blob hash, exact sizes, one Linux amd64 runtime, the loaded/scanned configuration digest and the whole archive SHA-256. It rejects links, traversal, duplicate JSON/members, unreferenced blobs and ambiguous runtime roots without extracting the archive.

The CI release manifest records image root/configuration digests, archive hashes, packaged app/migration chart hashes and an explicit database compatibility contract. It is itself hashed by the Phase 60 eligibility artifact. Large image archives are separate from the small manifest/chart evidence; downloads select exact artifact names and attempts, never every run artifact (Docker's proprietary build-record artifacts are not ZIP release bundles).

Before any cloud use, CI copies all three archives through a disposable loopback-only registry using the digest-pinned Skopeo image in `infra/release/toolchain.json`. It checks the destination raw manifest hash and pulls by digest to compare the resulting image configuration with the tested/scanned build. [Skopeo copy](https://github.com/podman-container-tools/skopeo/blob/main/docs/skopeo-copy.1.md) uses `--all --preserve-digests`; failure to preserve bytes must fail the release. The fixture's HTTP/TLS-verification exception is restricted to its hardcoded loopback registry. Real ECR copies must retain TLS verification. AWS documents [ECR manifest support](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-manifest-formats.html), but the local fixture does not prove live ECR/IAM behavior.

## Implemented promotion and rollback boundary

- Resolve a full commit SHA and exact successful main CI run using the trusted current-policy verifier, then verify downloaded manifest/chart/archive bytes before obtaining cloud credentials.
- Publish the verified OCI digests to environment-specific ECR repositories without rebuilding. Keep publisher, migration-owner and namespace application identities separate; never grant the publisher Kubernetes access.
- Use reviewed environment configuration and protected GitHub environments on an isolated private runner with EKS/DNS connectivity. No automatic deployment; execution remains explicitly approval-gated.
- Run one bounded, forward-only migration Job with the isolated migration identity. App deployment uses digest references and functional health checks. Bootstrap owns Services, TargetGroupBindings, NetworkPolicies and controllers.
- Rollback selects an explicitly compatible previously verified release and confirms actual database compatibility. It never performs database downgrade, force-removes finalizers or grants app access to migration credentials.

The initial compatibility declaration accepts schema V2 only. A future migration must deliberately update and test API/rollback compatibility rather than assuming every earlier image is safe. Negative revision/digest/artifact/schema tests and the real artifact/copy rehearsal passed; see the [Phase 61 review](archive/phase-reviews/phase-61.md). Live AWS validation remains approval-gated.
