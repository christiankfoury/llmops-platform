# Terraform-owned load balancing: Phase 59 investigation

Status: adopted after v3.5.0 source review and initial compatibility testing.
The final actual-template regression passed in [CI 34142470972](https://github.com/christiankfoury/production-ai-platform/actions/runs/34142470972)
on `67d3becbfb85c79edd7465561d7145789604754e`, including real EndpointSlices,
webhook readiness-gate injection and outage rejection. The [full CI suite](https://github.com/christiankfoury/production-ai-platform/actions/runs/34142470828)
passed on that same revision, including both security scans. No deployment or cloud
change is approved by this document. The KSV-0056 exception under
`security-proposals/` remains inactive and unapproved.

## Pinned source findings

The examined source is the upstream v3.5.0 release, downloaded from
`https://codeload.github.com/kubernetes-sigs/aws-load-balancer-controller/zip/refs/tags/v3.5.0`
with SHA-256 `68b5f50ecf117b0b15e2cb84e2841e25cefa8b2959f3489794c01d8c5780f719`.
The deployed chart pin remains the checksum-recorded 3.5.0 archive in
`infra/validation/charts.json`; the experiment does not fork its controller.

- [main.go](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/main.go)
  unconditionally constructs and registers the Ingress reconciler. The
  [feature-gate list](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/pkg/config/feature_gates.go)
  has no `EnableIngressController` switch. Removing Ingress reads would prevent
  its informer caches from synchronizing. Keep namespace-scoped get/list/watch,
  remove all Ingress and Ingress/status writes, create no IngressClass, and deny
  Ingress create/update in the watched application namespace through admission.
  A non-default annotation class alone is insufficient: IngressClass matching
  uses the class controller field independently of the annotation flag.
- [TGB reconciliation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/pkg/targetgroupbinding/resource_manager.go)
  uses EndpointSlices/pod information, DescribeTargetHealth, RegisterTargets,
  DeregisterTargets and DescribeVpcs. It patches TGB checkpoints, status and
  finalizers and may patch pod target-health readiness conditions. It does not
  need to create/delete user-owned bindings. Binding deletion must deregister
  targets before the controller removes its finalizer.
- [Networking reconciliation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/pkg/networking/networking_manager.go)
  still discovers cluster-tagged security groups and performs cleanup when
  `spec.networking` is absent. DescribeSecurityGroups is necessary. A fresh
  Terraform-owned security-group configuration must not contain the controller's
  old `elbv2.k8s.aws/targetGroupBinding=shared` rule markers. Old marked rules can
  trigger attempted revocation; withholding EC2 writes then prevents cleanup.
  Removing or transferring such rules on an existing cluster requires a reviewed,
  approval-gated ownership handoff, not a permission exception or finalizer bypass.
- The [TGB mutator](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/webhooks/elbv2/targetgroupbinding_mutator.go)
  supplies missing target type, IP family, VPC and protocol. Specify them
  explicitly. The [validator](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/webhooks/elbv2/targetgroupbinding_validator.go)
  performs target-group discovery and duplicate/immutability checks. Its checks
  do not replace an administrator's approved ARN/service/port allowlist.
- `spec.iamRoleArnToAssume` invokes STS; multicluster mode writes tracking
  ConfigMaps; `spec.networking` activates security-group management. Reject those
  capabilities and target-group name lookup, instance targets, alternate VPCs,
  alternate service names/ports and spec mutation. Disable Service, Gateway,
  Global Accelerator, WAF/Shield and shared backend-security-group management.

## Adopted ownership and authorization

Terraform owns the ALB, TLS listener, explicit host routing rules, security groups
and IP target groups. Bootstrap owns Services, EndpointSlice administration,
NetworkPolicies, controller identity/RBAC, admission and exact target bindings.
The ordinary app deployer continues to own application Deployments, not network
objects. Only RegisterTargets/DeregisterTargets may mutate AWS, scoped to exact
Terraform-produced target group ARNs. Necessary Describe operations are separate
read permissions; their account-wide discovery scope must be explicit.

The controller gets TGB read/list/watch and patch/update only for the approved
binding names, plus their status subresources. It gets no TGB create/delete.
Admission must enforce the ARN/name/service/port/VPC/IP/protocol tuple and immutable
specs even for the bootstrap identity. Kubernetes RBAC cannot enforce field-level
updates; granting patch without admission would leave a retargeting path.
Trusted cluster administrators can change admission itself and remain part of
the trust boundary.

Before installing these restrictions on an existing cluster, stop if the watched
namespace contains any Ingress, if another binding/controller uses the proposed
target groups, or if cluster-tagged security groups contain the old LBC shared-rule
markers. Inventory existing Ingress finalizers, ALB/listener/target-group ownership,
registered targets, IAM attachments and security-group rules. Prepare a reviewed
transfer/import/draining plan and obtain the required infrastructure/downtime
approval before changing them. Applying restricted RBAC first can strand old
Ingress finalizers; revocation of the old IAM policy can prevent legacy cleanup.
This repository's fresh-cluster tests do not authorize that migration. Do not
temporarily restore broad permissions or force-remove finalizers as a workaround.

The module defaults to `load_balancing = null`: no ALB, target groups or registration
policy is created until an approved cloud plan supplies configuration. Required
inputs are distinct API/web hosts, an existing approved ACM certificate covering
both hosts, an approved same-region ALB access-log bucket with delivery permissions,
and explicit client CIDRs. Internal ALB is the default. A TLS 443 listener returns
404 unless an exact host rule matches ports 8000/3000. API health uses
`/health/ready`; management port 9000 is excluded. Draining is 30 seconds. ALB
deletion protection and access logging are enabled. DNS, certificates and log
buckets are not created by this module and retain their approval gates.

Merge the Terraform `load_balancing_bootstrap_values.targetBindings` map into
reviewed bootstrap values with `targetBindingsEnabled=false` to install admission
and name-scoped RBAC first. Once Services and controller webhooks are ready, enable
binding creation before creating app pods. The application namespace enables
readiness-gate injection; verify the injected condition and ALB target health.
Existing pods need a reviewed rollout to receive this immutable pod field.
Pod mutation is fail-closed: a controller webhook outage blocks new pods instead
of admitting them without target readiness gates. Existing registered targets
continue to serve, but scaling/replacement needs controller recovery.

AWS's [ELB authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_elbv2.html)
does not support resource-scoping DescribeTargetGroups/DescribeTargetHealth.
EC2 DescribeVpcs/DescribeSecurityGroups remain discovery reads as well. Terraform
and the local authorization fixture consume the same policy template; discovery
is separate from exact-ARN registration writes.

## Validation and limits

The separate `TargetGroupBinding compatibility` CI workflow starts a disposable
Kubernetes 1.36.4 cluster with the pinned unmodified controller, real RBAC, CRDs,
upstream webhooks and native validating admission policies. It uses an explicit
test kubeconfig and a local AWS protocol fixture with fake credentials. The
fixture rejects unexpected management operations and other target groups.

Required positive cases: startup/cache sync/leader election; first registration;
pod readiness/status/checkpoint updates; endpoint removal; transient AWS failure
and recovery; controller restart; binding deletion and finalizer completion.
Required negative cases: controller Ingress/Service/EndpointSlice writes,
controller binding create/delete/spec retargeting, app deployer binding writes,
unapproved ARN/port/networking/role/multicluster settings, and bootstrap Ingress
creation. Tests must fail on unauthorized AWS calls during legitimate operation.

Local fixtures cannot prove actual AWS IAM evaluation, EKS CNI packet enforcement,
pod health from ALB, TLS, DNS, zonal behavior or real cloud failover. Later approved
cloud validation must exercise exact-role allowed/denied AWS calls, healthy pod
registration and draining, traffic and health checks, failover, and denial of
unapproved groups without changing them. Do not describe mock calls as live AWS
evidence or proceed to release solely because Trivy passes.

## Remaining risks

- A compromised controller can deregister every target in an approved group or
  register arbitrary reachable IPs in it. IAM target-group scoping does not bind
  individual target IPs to Kubernetes pods. Network reachability, restricted
  credentials, reviewed workloads and controller audit/health alerts still matter.
- The app deployer controls the pods selected by approved Services; it is a trusted
  application-code publisher. Admission does not make malicious app code safe.
- Controller pod/status access can affect readiness throughout its watched
  namespace. Scope it to one environment; do not share a controller identity
  between environment clusters.
- Admission and upstream webhook availability affect bootstrap and binding
  operations. Keep fail-closed policies, preserve existing registered targets
  during controller outages, and document reviewed recovery rather than skipping
  finalizers or broadening credentials.
- Terraform and the controller must never both own target attachments or the
  same security-group rules. Target groups must be dedicated to this platform;
  single-cluster cleanup deregisters targets it does not recognize.
