# Codex Workflow

Use this workflow for every implementation phase. Codex should continue sequentially through phases without waiting for human approval unless a stop condition applies.

## Autonomous Phase Loop

1. Read `AGENTS.md`.
2. Read `PROJECT_SPEC.md`.
3. Read `phases.md`.
4. Read `phases-progress.md`.
5. Identify the current phase marked as `In Progress`.
6. Read that phase's deliverables and acceptance criteria.
7. Plan the phase.
8. Implement only that phase.
9. Add or update tests/checks where appropriate.
10. Run safe validation commands.
11. Fix validation issues.
12. Update docs.
13. Update `phases-progress.md`.
14. Commit.
15. Push.
16. Self-review.
17. Continue automatically to the next phase.

Do not wait for human approval between normal app, code, documentation, local Docker, CI, test, Helm template, or static validation phases.

## Progress Update Requirements

When completing a phase, update `phases-progress.md` to:

- Mark the completed phase as `Completed`.
- Record implementation notes.
- Record validation results.
- Record security, reliability, and observability notes where relevant.
- Mark the next phase as `In Progress`.

## Stop Conditions And Human Approval Gates

Stop and request human approval before any action that could create cost, downtime, data loss, credential exposure, or production impact.

Codex must stop before:

- Running `terraform apply`.
- Running `terraform destroy`.
- Creating paid cloud resources.
- Modifying real AWS infrastructure.
- Deploying to production.
- Deleting cloud resources.
- Deleting databases, buckets, registries, clusters, namespaces, or secrets.
- Rotating or changing real secrets.
- Changing DNS or TLS for a real domain.
- Running destructive database migrations.
- Force-pushing shared branches.
- Disabling security checks.
- Bypassing CI/CD approval gates.
- Exposing credentials in logs, commits, or workflow output.

For infrastructure phases, Codex may still safely:

- Write Terraform code.
- Write Kubernetes manifests.
- Write Helm charts.
- Write GitHub Actions workflows.
- Run `terraform fmt`.
- Run `terraform validate`.
- Run `helm lint`.
- Run `helm template`.
- Run unit tests.
- Run static checks.
- Build local Docker images.
- Update documentation.
- Commit and push code.

## Loop Completion

The autonomous loop ends only when:

- All phases are marked `Completed`.
- A stop condition requires human approval.
- A blocker prevents safe progress.
- Validation fails and Codex cannot fix it safely.
- Required credentials/access are missing.
- Proceeding would violate the current phase scope.

## Required Phase Plan Format

```text
## Phase N Plan

Goal:
- ...

Files expected to change:
- ...

Implementation steps:
1. ...
2. ...

Validation:
- ...

Out of scope:
- ...
```

## Required Completion Report Format

```text
## Phase N Review

Summary:
- ...

Files changed:
- ...

Validation:
- ...

Security:
- ...

Reliability:
- ...

Observability:
- ...

Scope discipline:
- ...

Risks:
- ...

Next phase:
- ...

Commit:
- ...
```

## Stay Within Scope

Do not implement later-phase functionality unless it is required as a minimal placeholder.

Prefer small interfaces and TODOs over full implementation of future phases.

## When Blocked

If blocked:

1. Stop.
2. Document the blocker in `phases-progress.md`.
3. Explain the exact issue.
4. Suggest the smallest safe next step.
5. Do not skip to unrelated work unless explicitly instructed.
