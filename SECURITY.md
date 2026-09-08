# Security policy

This is a private portfolio project. AWS deployment and repository publication
remain gated; the current gateway uses a mock provider and the default dashboard
uses isolated synthetic fixtures. It is not offered as a production service or a
security certification.

## Report a concern

Contact the repository owner through an existing private channel. Do not put
credentials, customer content, tokens, database dumps or exploit details into a
public issue. Before public release, the owner must choose and verify a private
vulnerability-reporting channel; no email address or reporting SLA is invented here.

Include the affected commit, component, a minimal synthetic reproduction and
expected versus observed behavior. Redact credentials and personal data. Real
secret rotation, access changes and deployment actions require their normal approval.

## Required controls and known findings

- Keep full-history secret review, dependency audits, image scans, integration
  tests and CI eligibility blocking. Missing or skipped evidence is not a pass.
- No scanner exception is active. Documentation of a finding does not authorize
  an exception or a lower scan threshold.
- [Monitoring findings](docs/security/monitoring-vulnerability-backlog.md) remain
  deferred by the owner. Phase 62 is incomplete and is a release/deployment blocker.
- [The focused review](docs/security/phase-64-review.md) records authentication,
  project boundaries, IAM/RBAC, exposure, current evidence and practical limits.
- [Publication decisions](docs/publication-decisions.md) remain separate from
  preparation; no visibility change, license selection or public release is approved.
