# Portfolio completion plan

Owner decision: **2026-09-08**. Finish a credible operations portfolio with bounded
proof of the important capabilities. The cloud milestone is **one approved AWS
dev/demo environment**. Separate staging and production deployments are optional
future work, with existing configuration and static checks preserved.

## Required remaining scope

| Phase | Bounded deliverable | Completion evidence |
|---|---|---|
| 62 | Runnable monitoring finalization; vulnerability remediation remains deferred | Final eligible image set and compatibility remain launch blockers; preserve existing prototype evidence |
| 63 | One local rehearsal: short synthetic load, Redis outage/recovery, API restart/compatible rollback, PostgreSQL backup and restore into a new disposable target | Measured latency/errors/recovery, restored row checks and reproducible commands; local results labeled clearly |
| 64 | Focused secrets/auth/access/exposure review, existing mandatory scans, accurate README, small screenshot set and one concise demo script | Current scan/test references, safe synthetic assets, honest limitations and remaining license/publication decisions |
| 65 | Practical setup/approval checklist for one AWS dev/demo footprint | Current cost estimate, intended running period, account/access/secret/domain inputs, deployment/rollback and approval-gated cleanup plan |
| 66 | One explicitly approved AWS dev/demo deployment | Actual request/auth, protected dashboards, metrics/logs/traces, alert, release/rollback and cloud backup-configuration evidence; actual cost recorded |
| 69 | Explicitly approved repository publication and closeout | Current required CI/security evidence, owner-selected license, sanitized assets and claims matching measured behavior |

Phase 63 is active for planning; no implementation is completed by this scope
change. Continue independent 63-65 preparation under AGENTS.md, then stop for AWS
setup and approval before Phase 66. Phase 65 may finish a package whose launch
decision is **blocked**. Phase 62 and current mandatory CI must be resolved before
the monitoring/cloud release. The known Skopeo CI availability failure is a
separate first engineering task; verify its latest state in the next run.

## Optional work removed from this release

- Phase 67: separate staging deployment and cloud recovery exercise.
- Phase 68: separate production deployment/customer-production operating footprint.

These phases are marked **Skipped by owner scope decision**, not Completed.
Their original intent is retained in `phases.md` for explicit future reactivation.
No automatic staging/prod creation, promotion or new paid infrastructure is in
scope. Do not remove their existing code or weaken its applicable static checks.
After approved Phase 66, proceed to Phase 69's separate publication approval.

A private approved dev/demo deployment is sufficient. A public demo, customer
production, a real domain or TLS changes require their own applicable approval.
Do not claim production SLAs, high availability, tested multi-environment
operation or cloud restore measurements based only on local/static evidence.

## Execution limits

Reuse existing code, tests and runbooks. During implementation use the smallest
checks that cover the changed behavior; preserve every mandatory CI gate on the
phase candidate. Once relevant checks and acceptance pass, close and review the
phase. Expand investigation only for a concrete failure or unresolved finding.
Reassess slow work after 20-30 minutes and retain the result instead of repeating
unchanged successful experiments. No open-ended capacity benchmark, new audit
program or custom third-party distribution maintenance is required.

The focused security review still verifies secrets are absent, authorization and
least privilege work, public exposure is controlled and required scans are
current. Existing [monitoring vulnerability findings](security/monitoring-vulnerability-backlog.md)
remain deferred and documented. Do not suppress findings, restart their custom
rebuilds, or reinterpret deferral as deployment risk acceptance.

## AWS boundary and cost

Phase 65 estimates only the selected dev/demo footprint; historical staging/prod
cost tables are comparisons, not a spending plan. Refresh pricing and confirm
intended lifetime, persistent storage, backups, load balancer/network charges and
an explicit cleanup plan before seeking approval. Budget alerts are notifications,
not hard spending caps. The plan authorizes no apply/destroy, paid resource,
existing data deletion, real secret, DNS/TLS or publication action.

Use synthetic data and the mock LLM provider. Show one traceable release and
rollback, one actionable alert and the local restore evidence. Describe what was
measured, what remains untested and which optional configurations exist. That is
the completion boundary for this portfolio scope.
