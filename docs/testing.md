# Testing

Run the smallest checks relevant to a change during development. Every PR and merged
main revision must still pass the complete mandatory CI suite. A local build with
`-DskipTests` packages an image; it is not test evidence.

## Java

Use Java 21 and the committed Maven Wrapper. Start a disposable Redis instance on
port 56379 as described in [Java reliability](java-reliability.md), then:

```sh
cd apps/api-java
./mvnw --batch-mode --no-transfer-progress --strict-checksums clean verify
```

On Windows use `mvnw.cmd`. Required PostgreSQL tests start their own disposable native
instance; startup failures fail validation. Redis must be available for its actual
integration tests. See the [Java README](../apps/api-java/README.md) for local cache and
Windows socket-path details. Checks cover formatting, compiler/static requirements,
HTTP boundaries, schema/adoption, authorization, limits, privacy and data-service TLS.
No required database test may be counted as passed when skipped.

## Frontend

From `apps/web`:

```sh
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npm audit --audit-level=high
```

Tests cover dashboard data/filtering, request inspection, synthetic fixture consistency,
isolation, session/CSRF and OIDC boundaries. Validate the actual application at desktop
and mobile widths after UI changes. [Screenshot procedure](dashboard-screenshots.md)

## Python reference and infrastructure

The Python runtime preserves migration/telemetry compatibility. Use
`make python-reference-check` with the configured virtualenv and required PostgreSQL
fixture environment. On Unix, override `API_PYTHON=.venv/bin/python`.
It is not the default Compose runtime. Do not run Alembic inside the Java container.

Workflow/policy checks use actionlint and `scripts/validate_ci_policy.py` plus
`scripts/tests`. Infrastructure checks include Terraform format/validate/mocked tests,
Helm rendering, Kubernetes schemas and policy, and the isolated controller lifecycle.
Use the commands and pinned tool versions in CI; never run AWS apply as validation.

## Complete CI and evidence

The [CI guide](ci-cd.md) defines all mandatory jobs, real PostgreSQL/Redis/container
checks, dependency/image/secret scans and immutable OCI promotion. PR validation has
read-only credentials; only trusted main writes images to private GHCR. Main's exact
revision and same-attempt artifacts must pass eligibility verification.

Use `make check` for Java and frontend local checks once their prerequisites are ready.
This does not replace the full CI security/infrastructure suite. Keep caches, 14-day
report retention, job timeouts and the approved Actions budget. Diagnose failures
before a bounded retry; do not suppress a scanner finding to complete a release.
