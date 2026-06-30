# Phase Review Prompt

Use this prompt after Codex completes each phase.

```text
Review the pushed phase commit before Codex automatically continues to the next phase.

Check whether the implementation:
1. Matches the phase scope in phases.md.
2. Avoids unrelated future-phase work.
3. Updates phases-progress.md correctly.
4. Includes appropriate tests or clearly documents why tests were not added.
5. Runs relevant validation commands.
6. Handles secrets safely.
7. Avoids hardcoded credentials, account IDs, tokens, or sensitive values.
8. Uses secure defaults where applicable.
9. Includes appropriate error handling.
10. Preserves local developer experience.
11. Keeps infrastructure changes environment-aware.
12. Keeps Kubernetes resources production-conscious with probes/resources where relevant.
13. Maintains clear documentation.
14. Does not perform stop-condition actions without human approval.
15. Correctly identifies whether the autonomous loop should continue or stop.
16. Was pushed to `main` without bypassing branch protection or CI/CD approval gates.
17. Identifies the top actionable findings from the pushed commit.
18. Uses one separate follow-up commit for each accepted fix.

Report:
- Summary
- Files changed
- Validation
- Scope issues
- Bugs or correctness issues
- Security concerns
- Reliability concerns
- Observability concerns
- Missing tests
- Documentation gaps
- Top findings from pushed commit
- Follow-up fix commits
- Stop condition or approval needs
- Risks
- Next phase
```
