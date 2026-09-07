# Java API migration

Phases 50-57 implement the Java 21/Spring Boot service, PostgreSQL/Flyway, mock gateway, both clients' telemetry, dashboard/configuration APIs, OIDC project authorization and key lifecycle. Docker Compose, Helm and deployment remain on the Python reference until Phase 58. AWS remains the cloud target. See [operator setup](../../docs/java-operator-security.md), [gateway behavior](../../docs/java-gateway.md) and [telemetry contracts](../../docs/java-telemetry.md). Distributed Redis limits and dependency readiness are implemented; see [reliability settings and required Redis fixture](../../docs/java-reliability.md). [Java metrics, structured logs and traces](../../docs/java-observability.md) are implemented. The runnable monitoring stack follows in Phase 62.

The build uses Java 21, Spring Boot 4.1.1, Maven 3.9.16, Maven Wrapper 3.3.4, Spotless 3.10.2 and Google Java Format 1.28.0. The Spring Boot BOM pins library versions; the build rejects snapshot dependencies, checks Java/Maven versions, treats compiler warnings as errors, checks formatting and runs tests. Distribution downloads have a pinned SHA-256 checksum and CI checks the committed wrapper files before executing them. Dependency vulnerability and release SBOM gates are expanded in Phase 60; checksum validation alone is not a vulnerability scan.

From this directory:

```powershell
.\mvnw.cmd --batch-mode --no-transfer-progress --strict-checksums clean verify
.\mvnw.cmd --batch-mode --no-transfer-progress spotless:apply
```

On Linux/macOS, use `./mvnw` with the same arguments. Maven does not need to be installed separately. A Java 21 JDK and network access to Maven Central are needed for the first build. Set `JAVA_HOME` if Java 21 is not the default. For an isolated Windows workspace cache:

```powershell
$env:MAVEN_USER_HOME = (Resolve-Path ..\..).Path + '\.maven-cache'
.\mvnw.cmd --batch-mode --no-transfer-progress --strict-checksums "-Dmaven.repo.local=$env:MAVEN_USER_HOME\repository" clean verify
```

Before starting the service, configure and explicitly migrate a disposable PostgreSQL database using the [migration handover guide](../../docs/database-migration-handover.md). Runtime migrations and synthetic seeds are disabled by default. Hibernate validates the existing schema. Maven tests start an isolated PostgreSQL 16.15 server automatically and require a real disposable Redis on port 56379. Dependency startup/connection failures fail tests without skips. Start the [Redis fixture](../../docs/java-reliability.md#required-validation-and-local-fixture) before running Maven.

The service listens on `127.0.0.1:8080`; `API_BIND_ADDRESS` and `PORT` control the bind address and port. `/health` identifies the service, `/health/live` checks lifecycle liveness, and `/health/ready` reports whether the process accepts traffic. Readiness requires fresh successful PostgreSQL/Redis checks and refuses new work during draining. Liveness remains independent of those dependencies. Actuator health and Prometheus use the separate loopback management listener on port 9080. Health details, diagnostic/configuration/dump endpoints and JMX remain disabled; main-port Actuator paths return 404.

If a Windows launch fails inside `PipeImpl` with `Unable to establish loopback connection`, use an existing workspace directory for temporary sockets. This was required by the local desktop launch environment during Phase 50; it is not a production JVM setting:

```powershell
$taskSocketDirectory = Join-Path (Resolve-Path ..\..).Path '.maven-cache/java-tmp'
New-Item -ItemType Directory -Force -Path $taskSocketDirectory | Out-Null
java "-Djdk.net.unixdomain.tmpdir=$taskSocketDirectory" -jar target/production-ai-platform-api-0.1.0-SNAPSHOT.jar
```

The packaged service was smoke-tested locally with that setting. CI also starts the packaged JAR, checks health, and verifies that diagnostic and test-only routes return 404.

JSON uses snake_case, explicit nulls, ISO date strings and decimal strings. Unknown JSON properties are rejected. Validation uses 422 with a safe detail array; malformed bodies use 400; unexpected errors use a generic 500 without payload/exception text. Synthetic test endpoints exist only in the test classpath. The [migration contract](../../docs/java-migration-contract.md) records the compatibility rules and planned intentional changes.

References: [Spring Boot requirements](https://docs.spring.io/spring-boot/system-requirements.html), [Jackson integration](https://docs.spring.io/spring-boot/reference/features/json.html), [Maven Wrapper verification](https://maven.apache.org/tools/wrapper/).

Phase 53 ports Proofbase/AgentOps ingestion; see [Java telemetry](../../docs/java-telemetry.md) for source registration, replay compatibility, limits, transactions and client-capture validation.

Phase 54 ports usage and local configuration controls; see [Java operator APIs](../../docs/java-operator-apis.md) for response contracts, access boundaries, audit behavior and concurrency.

Phase 55 replaces the temporary local operator identity with OIDC/project grants. The default operator mode is closed; configure identity or select the frontend-only synthetic demo explicitly.
