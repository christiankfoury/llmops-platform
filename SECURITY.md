# Security policy

This repository is a development and infrastructure demonstration, not a hosted
production service. Current validation covers the Java application and its delivery
pipeline. AWS is not deployed; the monitoring release has known unresolved findings.

## Report a vulnerability

Use GitHub's private **Report a vulnerability** form:

[Submit a private security report](https://github.com/christiankfoury/llmops-platform/security/advisories/new)

Private reporting is selected for source publication and will be enabled and verified
as part of the visibility change. Publication status is tracked in
[the decision record](docs/publication-decisions.md). If the form is unavailable,
use your existing private contact with the repository owner while access remains
private. Do not post exploit details, credentials or customer information in a public issue.

Include the affected revision/component, a minimal synthetic reproduction, impact,
and expected versus observed behavior. Use placeholders instead of real secrets or
personal data. No response-time SLA or bug bounty is offered.

## Controls and limitations

- Application keys are hashed; operator access uses OIDC and project grants.
  Browser mutations retain session, origin and CSRF protections.
- Required CI includes full-history secrets, dependencies, runtime images,
  infrastructure policies and actual PostgreSQL/Redis integration tests.
- Scan results establish compliance with the selected policy, not absence of all
  vulnerabilities. No scanner exception is active.
- [Known monitoring findings](docs/security/monitoring-vulnerability-backlog.md)
  remain documented and block monitoring deployment. Source sharing is not
  deployment risk acceptance or a claim that these findings were fixed.
- The [security design](docs/java-operator-security.md) and
  [focused review](docs/security/phase-64-review.md) describe tested boundaries.

Real secret rotation, infrastructure changes and data deletion require their normal
approval. Never include raw secrets in logs, reports, issues or pull requests.
