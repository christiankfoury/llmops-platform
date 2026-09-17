# CI private GHCR storage review

## Summary and plan

Owner direction (2026-09-16): use private GHCR instead of paid Actions image
storage. Implement this as CI/release maintenance before Phase 66, independently
of the uncommitted Phase 62 monitoring proposal.

1. Retain tested/scanned OCI images in three fixed private GHCR packages.
2. Require TLS, immutable digests, package privacy and full blob read-back checks.
3. Keep PR execution read-only and all existing validation mandatory.
4. Retrieve the same image digests for preflight and future approved ECR promotion.
5. Validate, push to main, inspect current CI and review follow-up findings.

## Scope and files

CI image jobs and permissions, registry_images.py with negative tests, immutable
release preparation/execution, release workflow read permissions, CI/eligibility
policy tests and active runbooks. Small reports remain Actions artifacts.
No application code, dependencies, monitoring prototypes, AWS resources, real
secrets, account billing settings or repository visibility changed.

## Validation

- `python -m unittest discover -s scripts/tests -p 'test_*.py' -q`: 36 passed.
- Ruff lint and formatting of changed Python helpers/tests passed.
- CI policy validation passed: one scoped main writer, identical read-only PR
  checks, complete applicable dependencies and unchanged AWS execution holds.
- Actionlint passed for CI and all release entry points (local ShellCheck was not
  available; expression/YAML validation ran, and required CI keeps its checks).
- Existing Helm release validation passed for dev/staging/prod, including rejected
  mutable references and unsafe inputs. No AWS deployment is inferred.
- New tests reject changed OCI blobs/configuration/root manifests, foreign/mutable
  registry references, public/unlinked packages, unsupported publication contexts
  and missing/skipped context-specific image validation.
- Real private GHCR push/read-back and full current-revision CI remain to be
  verified by the pushed candidate. Historical green runs are not substitutes.

## Security, reliability and observability

Only trusted main's image job receives packages:write. PRs use the same anchored
image build/test/scan steps with read-only permissions. The two contexts are
explicit: main has eleven passing mandatory jobs and one inactive PR counterpart;
PRs must pass their image job. No applicable job skip counts as success.

The GITHUB_TOKEN is passed only to the guarded storage step, written to a short-
lived mode-0600 auth file, mounted read-only and never included in command-line
credentials or logs. Private package metadata is checked before/after transfer;
new packages require the known private repository. Existing package visibility
is never changed. No new PAT, authentication bypass or scanner exception exists.

Build provenance retains the original OCI export SHA-256. Registry tar headers
can change during transport; every content blob and the root/runtime/configuration
digests remain mandatory. Charts, manifests, values, plans and historical archive
hashes retain exact-file verification. GHCR-only images cannot replace missing or
expired CI evidence. Registry failures block release eligibility.

## Risks and post-commit review

GHCR container storage/bandwidth are currently free, not a permanent pricing
promise. Hosted-runner minutes and small artifact allowances still apply. Paid
usage remains disabled by owner intent; no account billing change was made.
The existing Actions quota/usage accounting block may still prevent small report
uploads until GitHub permits them. Do not mask that failure or weaken evidence.
Private GHCR behavior and current CI must be inspected after push; any actionable
findings receive separate follow-up commits and relevant validation.

Phase 62 remains Blocked; Phase 66 AWS setup/approval and all publication gates
remain. Optional staging/prod remain skipped. No source publication was performed.
