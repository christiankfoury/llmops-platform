# Documentation

Two reading paths:

- **Backend / AI engineering:** [gateway](java-gateway.md), [operator authorization](java-operator-security.md), [telemetry contracts](external-telemetry-contract.md), [tests](testing.md).
- **Platform / DevOps:** [delivery](ci-cd.md), [infrastructure ownership](targetgroupbinding-design.md), [observability](observability.md), [recovery](local-recovery-rehearsal.md).

| Topic | Start here | Supporting material |
|---|---|---|
| Local setup and demo | [Run locally](deployment.md) | [Walkthrough](demo-script.md), [screenshots](dashboard-screenshots.md) |
| Architecture | [System architecture](architecture.md) | [Decisions](decision-log.md), [gateway](java-gateway.md), [API contracts](java-operator-apis.md) |
| Security | [Security policy](../SECURITY.md) | [Operator access](java-operator-security.md), [baseline](security-baseline.md), [known monitoring findings](security/monitoring-vulnerability-backlog.md) |
| Tests and CI | [Testing](testing.md) | [CI/CD](ci-cd.md), [supply-chain review](security/phase-64-review.md) |
| Deployment and releases | [Deployment boundaries](deployment.md) | [Immutable releases](immutable-release-runbook.md), [AWS checklist](aws-launch-checklist.md), [Terraform](terraform.md) |
| Observability | [Signals and monitoring status](observability.md) | [Java signals](java-observability.md), [incident response](incident-response.md) |
| Reliability | [Local recovery rehearsal](local-recovery-rehearsal.md) | [Backup/restore](backup-restore.md), [runbook](runbook.md) |
| Costs | [Cost analysis](cost-analysis.md) | [CI spending policy](ci-cd.md) |
| Client integrations | [Proofbase](proofbase-integration.md) | [AgentOps](agentops-integration.md), [telemetry contract](external-telemetry-contract.md) |

AWS deployment and monitoring finalization remain outstanding. [Current progress](../phases-progress.md)
and [publication decisions](publication-decisions.md) describe the boundaries.
Historical plans and dated evidence are in the [implementation archive](archive/README.md).

[Source publication review](security/publication-review.md) records exposure coverage and limitations.
