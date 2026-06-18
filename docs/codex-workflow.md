# Codex Workflow

Use this workflow for every implementation phase.

## Phase loop

1. Read `AGENTS.md`.
2. Read `PROJECT_SPEC.md`.
3. Read `phases.md`.
4. Read `phases-progress.md`.
5. Identify the current phase.
6. Plan the phase.
7. Implement only that phase.
8. Run checks.
9. Fix issues.
10. Update docs.
11. Update `phases-progress.md`.
12. Commit.
13. Push.
14. Self-review.
15. Continue to the next phase.

## Required phase plan format

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

## Required completion report format

```text
## Phase N Completed

Summary:
- ...

Files changed:
- ...

Validation:
- ...

Security notes:
- ...

Reliability notes:
- ...

Observability notes:
- ...

Scope check:
- ...

Commit:
- ...
```

## Stay within scope

Do not implement later-phase functionality unless it is required as a minimal placeholder.

Prefer small interfaces and TODOs over full implementation of future phases.

## When blocked

If blocked:

1. Stop.
2. Document the blocker in `phases-progress.md`.
3. Explain the exact issue.
4. Suggest the smallest safe next step.
5. Do not skip to unrelated work unless explicitly instructed.
