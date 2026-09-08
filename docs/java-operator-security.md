# Java operator access and key lifecycle

Phase 55 adds OIDC operator authentication, project grants, dashboard sessions, application key management and an isolated synthetic demo. AWS remains the target. Java became the default Docker/Helm runtime in completed Phase 58. These local tests are not evidence of a deployed AWS identity, ingress or production environment.

## Identity and project access

The Java API defaults to `OPERATOR_AUTH_MODE=disabled`: every usage read, operator identity and admin endpoint requires authentication and is closed when identity is unconfigured. Gateway completions and telemetry retain their separate machine-key contract. A machine API key, cookie, query token or caller-supplied actor/role header cannot authenticate an operator.

With `OPERATOR_AUTH_MODE=oidc`, Spring Security verifies RS256 signatures against an explicit trusted JWKS endpoint, exact issuer and API audience, expiration/not-before timestamps with 30 seconds of clock tolerance, required issuance/expiry/subject, and bounded identity/token values. Future issuance is refused. Cognito tokens must have `token_use=access` when that claim is present. ID tokens are not API access tokens. JWKS HTTP connect/read timeouts are two seconds; discovery is not required to start Java. HTTPS is required except explicit loopback HTTP in local/test environments.

`operator_project_grants` stores `(issuer, subject, project_id)` with `viewer` or `operator` and an active flag. No JWT role, group or project claim creates a grant. Viewers can read their granted projects; operators can also change configuration and manage keys there. Every query is constrained to active granted projects. An explicitly ungranted project filter returns 403; ungranted object lookups/mutations return 404. A valid identity with no grants sees empty lists. Inactive projects or revoked grants cease authorizing new requests. Mutations lock the project and recheck the grant after acquiring the lock, serializing them with grant changes through the provisioning command.

`GET /v1/operator/me` returns `authenticated`, a verified `actor_id` and the caller's project/role list. Configuration/key audits use actor type `operator` and `oidc:` plus SHA-256 of the issuer, a newline separator and subject. Raw subject values, JWTs and caller actor headers are excluded from these audit records. This is attribution, not a tamper-proof external audit archive.

## Configuration

| Component | Required settings when OIDC is enabled |
|---|---|
| Java | `OPERATOR_AUTH_MODE=oidc`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URI`; existing JDBC/schema settings remain required. |
| Next.js | `WEB_AUTH_MODE=oidc`, fixed `WEB_ORIGIN`, the same `OIDC_ISSUER` and `OIDC_AUDIENCE`, `OIDC_CLIENT_ID`, `WEB_SESSION_SECRET`, server-only `API_BASE_URL`; confidential clients also supply `OIDC_CLIENT_SECRET`. |
| Both | Explicit `ENVIRONMENT` (`local`/`test` permit loopback HTTP; hosted identity/browser endpoints use HTTPS). |

`WEB_ORIGIN` is the exact browser origin. Register `${WEB_ORIGIN}/api/auth/callback` as an exact redirect URI with the identity provider. Enable authorization code flow, PKCE S256 and the `openid` scope. Use an API resource audience distinct from the dashboard client ID. For Cognito managed login, configure resource binding: the dashboard sends the API audience in the OAuth `resource` parameter so the access token contains the `aud` claim enforced by Java. A Cognito access token with only `client_id` is insufficient for this audience check.

The browser receives only `/api/platform` as its API base. Internal API addresses and identity credentials are not public runtime config. `API_BASE_URL` accepts an explicit HTTP internal service origin or HTTPS origin without credentials/path/query. Network and transport policies for the internal hop are verified in Phase 58. The default bind remains loopback until that cutover.

Generate a random 32-byte base64url session encryption secret in the local shell without printing or committing it, for example in PowerShell:

```powershell
$env:WEB_SESSION_SECRET = node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('base64url'))"
```

Use approved secret delivery for hosted values. Real identity configuration, grants, client secrets and cloud changes remain subject to the existing environment approval gates. Example files contain no working credentials.

## Explicit grant provisioning

Flyway V2 adds the grant table and role/uniqueness constraints without changing legacy rows. Apply/adopt migrations through the existing migration JAR before provisioned grants. There is no public self-grant endpoint, default superuser or automatically granted seed identity.

Use a trusted, dedicated database-owner connection and the migration artifact with `grant-operator` or `revoke-operator-grant`. Supply the existing JDBC credentials/schema plus `OIDC_ISSUER`, `OPERATOR_SUBJECT`, `OPERATOR_PROJECT_SLUG` and `OPERATOR_ROLE` (`viewer` or `operator`) through environment settings. The command requires an HTTPS issuer, an existing project and successful V2 migration; grant creation requires an active project. Revocation can operate on an inactive project. It never applies migrations implicitly.

```text
java -jar target/production-ai-platform-api-0.1.0-SNAPSHOT-migration.jar grant-operator
java -jar target/production-ai-platform-api-0.1.0-SNAPSHOT-migration.jar revoke-operator-grant
```

The command locks the project and changes the grant and its audit atomically with five-second SQL/lock timeouts. Bootstrap audit actor type is `database_owner`, actor ID is `database:` plus the database session user, and metadata contains only role/activity. A shared database role cannot distinguish individual humans; restrict its use and preserve the surrounding approved execution record. Do not give the application runtime a self-service grant-management capability. AWS database-role separation is completed with deployment hardening.

## Dashboard session and CSRF boundary

Next.js performs the code exchange on the server using pinned `openid-client`, with fresh PKCE verifier/challenge, state and nonce, a fixed callback URI, and explicit ID-token signature verification. It asks the Java identity endpoint to validate the access token before creating a session. Failed callbacks use fixed errors and clear the flow cookie; no callback code, token or provider diagnostics are logged. The provider enforces single-use authorization codes.

Flow cookies expire in five minutes. Session cookies contain an authenticated-encrypted JWE, a backend access token and a random CSRF token. They expire within 15 minutes and no later than the provider's reported access-token lifetime. Cookies are HttpOnly, SameSite=Lax, path `/`, with Secure and the `__Host-` prefix on HTTPS origins; no Domain is set. The encrypted cookie has a strict size cap. No ID/refresh token is retained and no access token enters browser JavaScript or localStorage. Session responses expose only identity/grants, expiry and the CSRF token.

The server proxy permits only the usage and admin/key routes, fixes the upstream origin, strips incoming credentials/actor headers, does not follow redirects, bounds URL/request/response sizes and uses a five-second fetch timeout. POST/PATCH and logout require both the configured Origin and a matching constant-time CSRF header. Responses are not cacheable. Java's CSRF filter is disabled specifically because that API accepts explicit Authorization/API-key headers and never authenticates browser cookies; the cookie boundary is protected in Next.js.

Logout clears the browser cookies. These sessions are stateless: a copied valid cookie/access token is not centrally invalidated by logout and can remain usable until its short expiry. Revoking a project grant blocks subsequent project access immediately; it does not cancel already admitted requests. Refresh and identity-provider-wide logout are not implemented. Do not claim immediate global token revocation.

## Application keys

| Endpoint | Required grant | Result |
|---|---|---|
| GET `/v1/admin/applications/{id}/api-keys` | viewer or operator | Bounded list of ID, prefix, description, activity, last-used/revocation/creation timestamps. No hash or raw key. |
| POST the same path | operator | Optional bounded `description`; returns 201 with `key` metadata and `api_key` exactly once. |
| POST `/v1/admin/api-keys/{id}/revoke` | operator | Idempotent revocation; repeating it does not create another revocation audit. |

Generated keys use 256 bits from `SecureRandom`, a `pap_` prefix and URL-safe encoding; PostgreSQL stores only SHA-256 and a short display prefix. Creation/revocation and verified audit records commit together. Inactive applications cannot receive new keys; their keys can still be listed/revoked. Authentication requires an active, unrevoked key, active application and active project.

Last-used timestamps update at most once per minute in committed gateway/event-recording transactions, including accepted duplicate telemetry. Invalid/failed admission does not update them. The conditional update touches timestamps only and cannot reactivate a revoked key. Writers insert their project-linked request before touching the key; key administration locks project then key to preserve the lock order. Revocation blocks subsequent authentication; it does not cancel work that has already authenticated. No automatic rotation of real keys occurs.

## Isolated synthetic demo

`WEB_AUTH_MODE=synthetic_demo` serves fixed fixture records from Next.js. This branch does not construct an OIDC client, read platform data or call the API/provider. All writes are rejected, unsupported paths remain closed, and the UI labels the data as a read-only synthetic demo. It is intentionally separate from seeded development databases and customer telemetry. `WEB_AUTH_MODE=disabled` is the default; no fallback from failed OIDC authentication enables demo access.

## Evidence and limits

Java tests use actual disposable PostgreSQL and an ephemeral local RSA/JWKS issuer. They cover signature/issuer/audience/time/purpose failures, machine/operator separation, viewer/operator roles, missing/revoked/inactive grants, scoped reads/writes, one-time key responses, revocation, last-used timestamps and atomic audits. Frontend tests exercise encryption/tampering/expiry, origin/CSRF, proxy allowlists and credential stripping, fixed demo isolation, and a complete local authorization-code exchange including replay and invalid ID signatures.

The packaged CI smoke starts a test-only issuer from `scripts/fixtures/OperatorIdentityFixture.java`, creates grants through the actual migration JAR, and tests anonymous refusal plus authenticated dashboard reads/configuration after gateway and both clients' telemetry/replays. The fixture is not part of the production JAR and its ephemeral private key is never written. Local processes and the temporary credential file are cleaned up. No AWS/Cognito account or paid provider is involved. Redis admission/readiness, full observability and runtime cutover follow in Phases 56-58.

References: [Spring JWT resource server](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html), [OIDC code-grant checks](https://github.com/panva/openid-client/blob/main/docs/functions/authorizationCodeGrant.md), [explicit ID signature checks](https://github.com/panva/openid-client/blob/main/docs/functions/enableNonRepudiationChecks.md), [Cognito resource binding](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html).
