package dev.christiankfoury.aiplatform;

import io.zonky.test.db.postgres.embedded.EmbeddedPostgres;
import java.io.IOException;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/** A real, isolated PostgreSQL 16 server; initialization errors fail the suite, never skip it. */
abstract class PostgresTestSupport {
  static final EmbeddedPostgres POSTGRES = startPostgres();
  static final String REDIS_NAMESPACE = "test-" + java.util.UUID.randomUUID();

  private static EmbeddedPostgres startPostgres() {
    try {
      EmbeddedPostgres postgres = EmbeddedPostgres.builder().setPort(0).start();
      Runtime.getRuntime()
          .addShutdownHook(
              new Thread(
                  () -> {
                    try {
                      postgres.close();
                    } catch (IOException exception) {
                      throw new IllegalStateException("Test PostgreSQL shutdown failed", exception);
                    }
                  }));
      return postgres;
    } catch (IOException exception) {
      throw new IllegalStateException("Required test PostgreSQL could not start", exception);
    }
  }

  @DynamicPropertySource
  static void databaseProperties(DynamicPropertyRegistry registry) {
    registry.add(
        "platform.redis.host", () -> System.getenv().getOrDefault("TEST_REDIS_HOST", "127.0.0.1"));
    registry.add(
        "platform.redis.port", () -> System.getenv().getOrDefault("TEST_REDIS_PORT", "56379"));
    registry.add("platform.limits.namespace", () -> REDIS_NAMESPACE);

    registry.add("spring.datasource.url", () -> POSTGRES.getJdbcUrl("postgres", "postgres"));
    registry.add("spring.datasource.username", () -> "postgres");
    registry.add("spring.datasource.password", () -> "postgres");
    registry.add("spring.flyway.enabled", () -> "true");
  }
}
