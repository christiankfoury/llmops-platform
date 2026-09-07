# Java runtime cutover

Phase 58 switches default Compose and Kubernetes packaging to Java 21/Spring Boot. AWS remains the target. Runtime acceptance is tracked in the [phase review](phase-reviews/phase-58.md); AWS deployment, immutable promotion and monitoring installation require the subsequent phases. Existing deployment/rollback jobs have an explicit cutover hold so manual dispatch cannot publish a Python image against the new Java chart. Phase 61 replaces those jobs before the hold is removed. No AWS resources or real secrets are changed by the cutover code.

## Fresh local stack

From the repository root, with a Linux Docker engine available:

```bash
docker compose up --build --wait
curl --fail http://localhost:8000/health/ready
```

Compose runs an explicit one-shot Flyway migration before the Java API. Local-only startup seeding creates the demo, Proofbase and AgentOps scopes with the documented synthetic keys. Visit `http://localhost:3000` for the **isolated synthetic dashboard**. Its fixed data does not reflect newly ingested events. Real usage/configuration requires [OIDC sign-in and explicit project grants](java-operator-security.md); anonymous operator APIs remain closed.

```bash
# Repeat safely against this disposable local stack, if needed:
docker compose run --rm migration
docker compose run --rm migration java -jar /app/migration.jar seed-local
# Private management listener; never published to the host:
docker compose exec api java -Xms16m -Xmx32m -cp /app/probe HttpProbe metrics
# Stop containers; retain the local database volume:
docker compose down
```

Compose binds exposed ports only to host loopback: web 3000, API 8000, PostgreSQL 55432 and Redis 56379. Local data-service connections are plaintext only in the default local fixture. The TLS acceptance overlay below checks encrypted connections separately. The public API contract and both clients' telemetry URLs stay unchanged. No real model provider is called.

The new `ai-platform-java-local` Compose project and `java-postgres-data` volume avoid implicitly adopting an old Python database. The explicit Python reference is `docker compose -f docker-compose.python-reference.yml up --build`; it is for local regression comparison and must not be public. Stop the other stack first or choose different host ports. The reference keeps its old database volume naming and Python migration commands. Do not delete volumes or switch migration ownership to resolve a port/schema error.

For an existing database, rehearse [verified Alembic adoption](database-migration-handover.md) on a restored copy. Java owns Flyway V1/V2 after adoption. Runtime Hibernate only validates; neither Java API startup nor a rollout performs DDL. A rollback uses a schema-compatible application or an approved restored replacement, never Alembic downgrade or removal of Flyway history.

## Images and resource budget

Build API and migration images from the repository root, and web from `apps/web`:

```bash
docker build -f apps/api-java/Dockerfile --target api -t production-ai-platform-api:local .
docker build -f apps/api-java/Dockerfile --target migration -t production-ai-platform-migration:local .
docker build -f apps/web/Dockerfile -t production-ai-platform-web:local apps/web
```

Temurin Java 21 JDK/JRE, Node 24 LTS and PostgreSQL 16.15 base indexes are pinned by digest. Redis 7.2.16 is pinned to its verified Linux amd64 manifest, matching the initial AWS node architecture; ARM is not validated. Maven builds both runnable JARs; required CI runs the real integration suite separately from image compilation. The runtime contains the JRE and application dependencies, without Maven or test tooling. Production web uses Next.js standalone output and Node 24.20.0.

API and migration run as UID/GID 10001, with a read-only root filesystem, no Linux capabilities, no privilege escalation and a writable 128 MiB `/tmp`. The 1 GiB container limit contains a 512 MiB maximum Java heap and 128 MiB direct-memory budget, leaving room for threads, metaspace, JVM native memory and tmpfs. Kubernetes requests 512 MiB and 250 millicores; load sizing remains Phase 63. The web uses UID/GID 10001, a 512 MiB limit and separate 64 MiB temporary/cache mounts.

Java container health checks call readiness. Kubernetes adds a liveness-based startup probe with a 180-second budget, dependency-aware readiness and independent liveness. The API receives 60 seconds for termination: five seconds pre-stop, then up to 40 seconds graceful shutdown, with margin. Pending work is bounded as described in [reliability](java-reliability.md).

## Kubernetes configuration and secrets

The Helm chart and raw Kustomize bases/overlays use the same ports, probes, resource budgets, writable mounts and Java settings. Charts default to closed operator/dashboard access. Set the nonsecret OIDC issuer/audience/JWKS, web client ID and HTTPS origin through reviewed values; `API_BASE_URL` defaults to the private API Service and is server-only. OIDC web mode reads a separate `ai-platform-web-session` Secret (`session-secret`, optional `oidc-client-secret`). The frontend never receives database/Redis credentials.

The API's `ai-platform-runtime-secrets` must contain these AWS Secrets Manager properties through External Secrets:

| Property | Java environment |
|---|---|
| `jdbc-database-url` | `JDBC_DATABASE_URL` |
| `database-username` | `DATABASE_USERNAME` |
| `database-password` | `DATABASE_PASSWORD` |
| `redis-host` | `REDIS_HOST` |
| `redis-port` | `REDIS_PORT` |
| `redis-username` | `REDIS_USERNAME` (empty for password-only auth) |
| `redis-password` | `REDIS_PASSWORD` |

Hosted JDBC URLs must use `sslmode=verify-full`, separate credentials and verified trust, for example `jdbc:postgresql://replace-with-rds-endpoint:5432/ai_platform?sslmode=verify-full&sslrootcert=/certificates/postgres-root.pem`. Duplicate URL parameters, URL credentials and custom verification bypass factories are refused before connecting. The public RDS CA bundle must be supplied as key `postgres-root.pem` in the referenced `ai-platform-database-ca` ConfigMap. This file is public trust material, never a client private key. Missing trust or credentials fails startup; the app does not synthesize cloud secrets.

Hosted Redis requires TLS and a password; use the actual ElastiCache DNS endpoint for hostname verification. Default JVM roots handle publicly trusted AWS certificates. For a private CA, use Temurin's retained CA entrypoint with explicit `USE_SYSTEM_CA_CERTS=1` and the public CA `.crt` files mounted in `/certificates`; it prepares the JVM truststore in writable `/tmp` while running non-root. The RDS `.pem` is used directly by pgJDBC, not imported as a multi-certificate JVM alias. See [pgJDBC TLS](https://jdbc.postgresql.org/documentation/ssl/) and [Temurin certificate support](https://hub.docker.com/_/eclipse-temurin).

The optional Helm migration Job is **disabled by default** and uses its own image and `ai-platform-migration-secrets` with the three JDBC properties. Database-owner credentials never enter the API container. It has a 180-second deadline and no automatic retry. Rendering it does not run it; a release must run and verify the migration before updating API traffic. Job execution, immutable image selection and migration-aware rollback are Phase 61. Privileged namespace/SecretStore bootstrap and role provisioning remain Phase 59.

Actuator listens on private port 9080. Only the dedicated ClusterIP metrics Service exposes `/actuator/prometheus`; the public API Service/Ingress uses port 8000 and returns 404 for Actuator paths. A NetworkPolicy permits 9080 only from pods matching both the `observability` namespace and the Prometheus pod selector. The cluster must enforce NetworkPolicy; configure the selector to the installed monitoring release. Do not disable the policy while enabling remote metrics. Without remote metrics, the listener stays loopback.

## Reproducible acceptance

`python scripts/validate_java_container_stack.py` requires the three prebuilt `:local` images and a Linux Docker engine. It creates a unique Compose project and short-lived synthetic PostgreSQL/Redis certificate roots under ignored `.maven-cache`, uses an empty env file, and never reads personal credentials. It checks fresh migrations, idempotent seeds, gateway accounting, all eight captured client events and replays, isolated web fixtures, private metrics, non-root/read-only execution and writable mounts. It proves PostgreSQL hostname rejection and Redis trust failure while preserving liveness. Only this script's containers are stopped afterward; volumes are retained.

`docker-compose.tls-test.yml` is the test-only TLS overlay; private fixture keys are mounted only in their database/Redis server, never in application images or commits. Main CI runs the full container check and scans all three images. Local Docker engine unavailability must be reported honestly; packaged JVM tests and manifest rendering do not replace container evidence.
