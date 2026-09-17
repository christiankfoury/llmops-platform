> Historical review (2026-09-08). Current source-publication ordering, MIT selection and demo updates are recorded in [publication decisions](../publication-decisions.md).

# Focused security and claims review â€” 2026-09-08

Scope: independent Phase 64 preparation, using current source, existing tests and
mandatory CI. This is not a new audit program or authorization to deploy/publish.
Phase 62's [monitoring backlog](monitoring-vulnerability-backlog.md) remains deferred.

## Reviewed boundaries

| Area | Source and evidence | Result / practical limit |
|---|---|---|
| Secrets | Full-history Gitleaks review; CI filesystem/dependency/image scans; placeholder-only examples | Phase 64 `ad8bcbf`, CI 34193634531 passed all 11 jobs. Its full-history scan reviewed 194 commits, ten existing synthetic findings, zero unreviewed. Java ran 280 tests with zero skips; dependency/repository/runtime image gates passed. No real credential report is printed. |
| Operator identity | Java `OperatorSecurityConfiguration`, token validator and `OperatorAuthorization`; JWT/project-grant integration tests | Unconfigured endpoints closed; issuer/audience/time/signature checked; active database grants bound by issuer/subject/project. Machine keys do not create operator access. Real hosted IdP and AWS remain untested. |
| Writes and keys | `ApplicationKeyService`, scoped admin services, `operator-proxy.ts` and session/CSRF tests | Viewer/operator distinction, active project checks, atomic audits, hashed storage and one-time key response. Browser writes need session/origin/CSRF; proxy rejects redirects and strips caller credentials. Logout does not instantly revoke a stolen unexpired session/token. |
| Demo isolation | `synthetic-demo.ts`, `operator-proxy.ts`, operator dashboard tests and local capture probes | Fixed fixtures branch precedes API fetch; admin POST/PATCH 403, key listing 404, wrong-project fixture count zero. Backend intentionally unreachable; no telemetry/customer/provider connection. |
| IAM/RBAC | Terraform IAM module; bootstrap `release-rbac.yaml` and load-balancer RBAC; existing static/mocked/TGB checks | Distinct publisher/migration/app roles. ECR publisher lacks EKS access; app/migration only describe the exact cluster. Namespace RBAC keeps bootstrap/TGB/Ingress writes out of application release. App namespace Secrets access for Helm and migration Job creation remain powerful trusted-runner capabilities. |
| Network/transport | Bootstrap network policies, Helm non-root/read-only runtime settings, private data services, existing TLS container tests | Loopback local ports; management port unpublished; TLS hostname/trust rejection is tested. Real private EKS endpoints, AWS identity/secret synchronization and actual network enforcement remain launch checks. |
| Supply chain | Immutable action/tool/image pins, all-environment static checks, three OCI images/SBOMs and exact-revision eligibility | No scanner exceptions or weakened thresholds. Skopeo availability repair is independently scanned and exercised. Known monitoring images are outside the completed release and remain blocked. |

The local screenshot image audit passed Trivy 0.70.0 with `HIGH,CRITICAL`,
`--ignore-unfixed`, `vuln,secret` and exit code 1 on findings. Alpine 3.24.1 and
application dependencies were recognized. [Capture evidence](../archive/phase-reviews/phase-64-evidence.json)
retains the exact image and report hash. An audit pass is a selected-policy result,
not proof that every dependency is free of vulnerabilities.

## Corrected claims

- README/security/demo entry points now describe Java and Flyway, atomic Redis
  limits, OIDC project grants, held manual immutable releases and private metrics.
- The default dashboard is explicitly fixed synthetic data; gateway/telemetry
  requests are not claimed to appear there. Real usage requires operator setup.
- The demo script no longer presents Python/Alembic as the current backend,
  automatic deployment as active, or monitoring definitions as an eligible live stack.
- New JPEG screenshots are actual browser output, visibly marked synthetic, with
  invented IDs and no customer content. They are not monitoring/AWS evidence.
- Optional staging/prod configuration stays intact and statically tested, without
  live deployment/HA/SLA claims. Local restore timings are not cloud RTO/RPO.

## Remaining decisions and blockers

Read-only GitHub inspection found a private repository, no license, no releases,
and zero deployment environments. [Publication decisions](../publication-decisions.md)
record the owner's future license, visibility and reporting-channel choices.
Phase 65 supplies AWS setup/cost inputs. Phase 62 final image eligibility,
compatibility/delivery and monitoring checks remain unresolved before Phase 66.
No risk acceptance, secret rotation, AWS modification or public exposure occurred.

The [phase review](../archive/phase-reviews/phase-64.md) records the final candidate CI and
post-push review. Preparation can complete with these explicit release blockers;
publication and deployment cannot.
