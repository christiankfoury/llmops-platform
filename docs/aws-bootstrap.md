# AWS bootstrap and application release boundaries

Phase 59 validates infrastructure offline. No AWS resources, paid services, real secrets, identity provider, DNS record or deployment has been created by this phase. AWS remains the target: EKS, ECR, RDS PostgreSQL, ElastiCache Redis and Secrets Manager. The old deployment workflows remain held until the immutable Java release sequence in Phase 61.

## Ownership

| Identity/release | Scope | Responsibilities |
|---|---|---|
| Account bootstrap owner | Account and state backend | Versioned encrypted private S3 state bucket, native lock access, existing trusted bootstrap role, one shared GitHub OIDC provider |
| Cluster bootstrap owner | One environment cluster | EKS access entries, managed add-ons, namespaces, controller releases, IAM readers, trust ConfigMaps, secret stores, RBAC and network bootstrap |
| App deployer | `ai-platform-ENV` only | Application Helm releases; no namespace, store, controller, RBAC or migration-job ownership |
| Migration runner | `ai-platform-ENV-migration` only | Create a reviewed migration Job and read its status/logs; no app or cluster writes, no direct Secret API access |
| Runtime secret reader | Runtime and web-session containers only | ESO JWT ServiceAccount `external-secrets/ai-platform-runtime-secrets` |
| Migration secret reader | Migration container only | ESO JWT ServiceAccount `external-secrets/ai-platform-migration-secrets` |

The app deployer can access its own namespace's secrets because Helm stores release history there and the deployer controls app pods. Database-owner credentials are in a separate namespace and a separate AWS reader policy. Creating a migration Job inherently authorizes owner-level SQL through its referenced secret, so the migration identity requires the separately protected `ENV-migration` GitHub environment. Normal app trust accepts only `repo:OWNER/REPO:environment:ENV`; the former direct-main subject is removed. Both roles require the STS audience. The cluster creator receives no implicit admin access; the required existing bootstrap principal has the explicit cluster-admin EKS access entry.

## Offline validation

Run from the repository root after installing PyYAML 6.0.3:

```powershell
python scripts/install_validation_tools.py
$env:PATH = "$PWD/.maven-cache/tools/pinned;" + $env:PATH
$env:AWS_EC2_METADATA_DISABLED = "true"
terraform fmt -check -recursive infra/terraform
foreach ($environment in @('dev', 'staging', 'prod')) {
  $env:TF_DATA_DIR = "$PWD/.maven-cache/terraform-$environment"
  terraform "-chdir=infra/terraform/environments/$environment" init -backend=false -input=false -lockfile=readonly
  terraform "-chdir=infra/terraform/environments/$environment" validate -no-color
  terraform "-chdir=infra/terraform/environments/$environment" test -no-color
}
python scripts/validate_java_manifests.py
python scripts/validate_aws_manifests.py
```

CI executes equivalent commands on Linux. All test providers are mocked and every run is plan-only; test teardown has no AWS resources to delete. Each root exercises the initial foundation and the post-policy add-on stage with computed IDs. The tests caught the former computed Secret-role count and security-group set-key problems. Provider locks include signed Windows/Linux AWS 6.63.0 and TLS 4.3.0 checksums. See [validation provenance](../infra/validation/README.md). Static checks do not prove regional capacity, IAM execution, Kubernetes admission or live packet enforcement.

## Account state and private runner prerequisites

The account owner must create or identify the approved S3 backend independently of environment state. Require versioning, encryption, public access blocking, restricted TLS-only access and recovery ownership. `backend.hcl.example` uses environment-specific keys and `use_lockfile=true`. Grant only the environment state object's Get/Put permissions and the lock object's Get/Put/Delete permissions, plus bucket listing constrained to the relevant prefix and required KMS permissions if a customer-managed key is selected. State is sensitive even though Redis uses an ephemeral input and a provider write-only argument. Never commit real backend values, credentials, state or plan files. Current examples use native S3 locking; existing DynamoDB-backed state needs a reviewed lock migration, not an automatic replacement. [HashiCorp S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3).

Create or identify the account-wide `https://token.actions.githubusercontent.com` provider once, with STS audience; environment modules look it up and do not compete to own it. Bootstrap identity and account state changes require approval. A Terraform backend-disabled check does not initialize this state.

EKS defaults to private endpoint access only. The later deployment runner must be a fresh, trusted runner inside the VPC or on a reviewed connected network, with routes and security-group access to the private EKS endpoint on TCP 443. Enable VPC DNS support/hostnames and Amazon-provided DNS or reviewed Route 53 Resolver forwarding. Verify the EKS hostname resolves to reachable private addresses, and verify STS/ECR/Secrets Manager endpoints and the public OIDC issuer separately. Do not enable public EKS access to work around a disconnected GitHub-hosted runner. No untrusted fork job may run on a deployment runner or receive its identity.

Private nodes now have NAT egress by default for image pulls and AWS APIs; disabling NAT without a complete endpoint/egress alternative is not a deployable configuration. One NAT gateway is currently shared across AZs: it has a recurring cost and an AZ outage dependency. Phase 63/65 must price and choose the accepted topology before cloud approval. RDS/Redis remain private and accept traffic only from the configured workload security groups. Current CIDRs are dev `10.20.0.0/16`, staging `10.30.0.0/16`, prod `10.40.0.0/16`; change Terraform and reviewed bootstrap values together.

## Ordered, approval-gated bootstrap

1. Complete Phase 65's read-only regional preflight and review a concrete plan/cost package. Kubernetes 1.36 and AL2023 are the current target. Required exact add-on builds are deliberately unset until `describe-addon-versions` confirms compatibility for VPC CNI, kube-proxy, CoreDNS, EBS CSI and metrics-server in the selected region. Mock test versions are syntax fixtures, not deployable recommendations. Verify RDS 16.15 availability, Redis 7.2 support, node capacity and controller compatibility. [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
2. After approval, the bootstrap owner initializes the real backend and applies the reviewed foundation with `bootstrap_addons_enabled=false`. EKS uses API access entries, standard support, explicit CNI/proxy add-ons and AL2023 nodes. CNI enables strict NetworkPolicy enforcement and has its own IRSA role; node roles no longer inherit CNI permissions.
3. The bootstrap owner creates the dedicated `platform-system` release namespace and installs `infra/bootstrap/ai-platform-bootstrap` with the exact environment CIDR and Terraform role outputs. Keep `externalSecretsEnabled=false`. This creates namespace/RBAC/trust and DNS/controller policies before ordinary controller pods start. It does not manage the existing `kube-system` namespace. The initial policies permit DNS, required HTTPS endpoints and private webhook traffic; migration egress is restricted to DNS and private PostgreSQL.
4. Review and approve the second Terraform plan with `bootstrap_addons_enabled=true`, then install CoreDNS, EBS CSI and metrics-server. Keep this flag true afterward; turning it off would plan add-on removal and is a stop condition. Verify CoreDNS resolution, the actual managed add-on pod labels/ports, EBS CSI readiness, `kubectl top nodes`, and successful/denied network probes before continuing. Strict CNI starts ordinary pods denied, which makes this order necessary. [CNI policy behavior](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [EKS metrics-server ports](https://docs.aws.amazon.com/eks/latest/userguide/metrics-server.html).
5. Install the separately pinned ESO chart archive in `external-secrets` using `infra/bootstrap/controllers/external-secrets.yaml`. Its controller can mint JWTs only for the two dedicated reader SAs through a resource-name-constrained Role; the controller itself has no AWS role. Install the pinned load balancer chart in `kube-system`, using its controller values plus exact cluster name, region, VPC ID and `watchNamespace=ai-platform-ENV`. Its bootstrap-created SA has the upstream controller policy. Verify webhook readiness and CRDs before the next step. Never commit rendered webhook TLS keys.
6. The database bootstrap owner creates distinct migration-owner and runtime database roles with reviewed least-privilege grants. Create real secret versions outside Terraform state through approved secret delivery. Runtime contains seven properties listed in [runtime cutover](java-runtime-cutover.md); migration contains only the three JDBC properties; web-session contains `session-secret` and `oidc-client-secret` (an empty string for a public OIDC client). Supply the same Redis AUTH value to runtime delivery and the ephemeral `TF_VAR_redis_auth_token`, never a tfvars file or logs. The write-only provider field prevents token persistence in state. Token/version changes are approved rotations, not routine deployment inputs.
7. Upgrade the bootstrap release with `externalSecretsEnabled=true`. Two v1 ClusterSecretStores restrict allowed namespaces, and three ExternalSecrets target runtime/web-session in the app namespace and owner credentials in the migration namespace. Wait for Ready without printing values. The public pinned RDS CA bundle is mounted in both namespaces; JDBC must use hostname verification and `/certificates/postgres-root.pem`.
8. Follow Phase 61's approved migration then immutable application promotion sequence. The migration chart is render-only for a standalone Job, not installed through Helm by the migration runner. The application chart and raw Kustomize overlays reference existing namespace, trust and secrets. They cannot install cluster controllers/stores. Monitoring storage consumers and running observability releases arrive in Phase 62; defining an encrypted gp3 StorageClass alone creates no EBS volume.

These are ordered operating instructions, not commands already executed. Real bootstrap installation, secrets, applies and releases remain subject to AGENTS.md gates.

## Existing installation handoff

The chart ownership split is safe for fresh installations. Do not upgrade an existing release that owns Namespace, ClusterSecretStore or ExternalSecret objects blindly: Helm may delete removed resources. Inventory ownership and back up metadata first, prepare an explicit keep/adopt transfer under the cluster bootstrap owner, and review the plan for no deletion or secret interruption. Similarly, changing Terraform IAM resource addresses or enabling API-only EKS authentication against an existing cluster requires an access-preserving state/import/move plan. No live state migration is automated in Phase 59.
