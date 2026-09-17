# Architecture diagrams

The [system architecture](architecture.md) explains current local behavior and the
unexecuted AWS design. These diagrams distinguish CI evidence from deployment.

## Delivery

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant PR as Pull request
  participant CI as GitHub Actions
  participant GHCR as Private GHCR
  participant Ops as Operator
  participant AWS as AWS dev/demo (planned)
  Dev->>PR: Propose focused change
  PR->>CI: Required tests and scans
  CI-->>PR: Aggregate validation result
  PR->>CI: Merge; run exact-main-revision checks
  CI->>GHCR: Store and verify tested immutable images
  CI-->>Ops: Verified evidence, deployment not authorized
  Note over Ops,AWS: Deployment holds remain until prerequisites and approval
  Ops->>AWS: Separately approved release or compatible rollback
```

## Planned AWS ownership

```mermaid
flowchart TB
  tf[Terraform] --> network[VPC and network controls]
  tf --> cluster[EKS]
  tf --> data[RDS and ElastiCache]
  tf --> identity[IAM and Secrets Manager]
  tf --> alb[ALB listeners and target groups]
  bootstrap[Cluster bootstrap] --> bindings[TargetGroupBindings]
  bindings --> controller[Restricted endpoint controller]
  controller --> alb
  release[Approved immutable release] --> helm[Helm application and migration jobs]
  helm --> cluster
```

AWS has not been deployed. The controller's restricted lifecycle and rendered
configuration are tested locally/in CI; live access, secret synchronization and
monitoring remain launch checks. [Ownership details](targetgroupbinding-design.md)
