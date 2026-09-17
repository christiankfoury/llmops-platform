# Project summary

LLMOps Platform combines a Java gateway and usage dashboard with reproducible
container delivery, Terraform/Helm configuration, project authorization and local
recovery evidence. [README](../README.md) · [Architecture](architecture.md)

| Demonstrated today | Remaining work |
|---|---|
| Java gateway, mock provider, hashed application keys and operational records | Paid provider adapters are outside the current scope. |
| OIDC/project-grant authorization and isolated synthetic dashboard | Hosted identity and real AWS access remain untested. |
| CI tests, scans, SBOMs and immutable OCI promotion | AWS release jobs remain held. |
| Local dependency recovery, compatible rollback and database restore | No cloud RTO/RPO, HA or production SLA is claimed. |
| Instrumented application and dated monitoring prototype evidence | Final monitoring image/security/compatibility gate remains blocked. |

Proofbase and AgentOps are telemetry clients with separate content and execution
ownership. Source publication can support technical review before the separately
approved AWS demonstration. See [progress](../phases-progress.md).
