# Portfolio demo preparation

The current deliverable is one [five-minute script](demo-script.md) and
[two actual synthetic browser captures](assets/screenshots/phase-64.md).
Reuse these instead of creating a second demo flow or a large screenshot set.

The story is the operating layer: a scoped Java gateway, protected usage APIs,
CI/security checks, Terraform/Helm packaging, immutable promotion, dependency
recovery and a measured local restore. Proofbase and AgentOps retain their product
and workflow responsibilities. Neither client supplies content for these captures.

Current claims may describe tested local behavior and static cloud configuration.
The default web view is read-only fixed data, not an API-backed telemetry feed.
The [Phase 62 prototype](phase-reviews/phase-62.md) is dated evidence with an
unresolved final image/security gate. Do not claim a secure complete monitoring
release, live AWS operation, production SLA, HA or tested staging/prod deployments.

A single private AWS dev/demo can satisfy Phase 66 after monitoring completion,
current CI, setup and explicit approval. Public exposure and real DNS/TLS need
separate authorization. Phase 69 retains the license and publication decisions;
[the decision record](publication-decisions.md) lists outstanding inputs.

Before sharing, use the current README, [focused security review](security/phase-64-review.md),
[unreleased notes](release-notes.md) and the exact evidence revision. Keep optional
staging/prod configuration labeled static and untested in AWS.
