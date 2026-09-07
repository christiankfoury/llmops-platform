# Build context is the repository root; .dockerignore excludes credentials/caches.
FROM eclipse-temurin:21-jdk-noble@sha256:75ce56643243c3db632be2ef259625fb42ee3be1334389659f7a1a61acb78783 AS build
WORKDIR /workspace/apps/api-java
COPY apps/api-java/ ./
COPY contracts/ /workspace/contracts/
RUN chmod +x mvnw \
    && sha256sum --check .mvn/wrapper/SHA256SUMS \
    && ./mvnw --batch-mode --no-transfer-progress --strict-checksums -DskipTests package \
    && javac --release 21 -Xlint:all -Werror -d /workspace/probe container/HttpProbe.java
# Integration tests run in required CI against real PostgreSQL/Redis before release eligibility.

FROM eclipse-temurin:21-jre-noble@sha256:96975602e131485862eb8cd32927face8a06d7591a5e865944b634a701d9df72 AS runtime
WORKDIR /app
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
ENV PORT=8000 \
    API_BIND_ADDRESS=0.0.0.0 \
    MANAGEMENT_PORT=9080 \
    MANAGEMENT_BIND_ADDRESS=127.0.0.1 \
    JAVA_TOOL_OPTIONS="-Xms128m -Xmx512m -XX:MaxDirectMemorySize=128m -XX:+ExitOnOutOfMemoryError -Djava.io.tmpdir=/tmp"
USER 10001:10001
# Retain Temurin's CA entrypoint: opt-in USE_SYSTEM_CA_CERTS adds mounted public
# certificates to a writable /tmp JVM trust store while root filesystem stays read-only.

FROM runtime AS migration
COPY --from=build /workspace/apps/api-java/target/production-ai-platform-api-0.1.0-SNAPSHOT-migration.jar /app/migration.jar
CMD ["java", "-jar", "/app/migration.jar", "migrate"]

FROM runtime AS api
COPY --from=build /workspace/apps/api-java/target/production-ai-platform-api-0.1.0-SNAPSHOT.jar /app/api.jar
COPY --from=build /workspace/probe/ /app/probe/
EXPOSE 8000 9080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=6 \
    CMD ["java", "-Xms16m", "-Xmx32m", "-cp", "/app/probe", "HttpProbe"]
CMD ["java", "-jar", "/app/api.jar"]
