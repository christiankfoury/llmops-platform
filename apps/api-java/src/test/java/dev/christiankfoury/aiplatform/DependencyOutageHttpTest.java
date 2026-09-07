package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.reliability.DependencyReadiness;
import dev.christiankfoury.aiplatform.reliability.DrainState;
import java.time.Duration;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class DependencyOutageHttpTest {
  private static final io.zonky.test.db.postgres.embedded.EmbeddedPostgres POSTGRES =
      PostgresTestSupport.POSTGRES;
  private static final TcpFaultProxy DATABASE = new TcpFaultProxy("127.0.0.1", POSTGRES.getPort());
  private static final TcpFaultProxy REDIS =
      new TcpFaultProxy(
          System.getenv().getOrDefault("TEST_REDIS_HOST", "127.0.0.1"),
          Integer.parseInt(System.getenv().getOrDefault("TEST_REDIS_PORT", "56379")));
  private static final String NAMESPACE = "outage-" + UUID.randomUUID();
  @Autowired MockMvc http;
  @Autowired javax.sql.DataSource webDatabase;
  @Autowired dev.christiankfoury.aiplatform.reliability.RedisSettings redisSettings;
  @Autowired DependencyReadiness readiness;

  @Autowired
  dev.christiankfoury.aiplatform.reliability.PlatformDependenciesHealth dependenciesHealth;

  @Autowired DrainState drain;

  @DynamicPropertySource
  static void proxies(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.username", () -> "postgres");
    registry.add("spring.datasource.password", () -> "postgres");
    registry.add("spring.flyway.enabled", () -> "true");

    registry.add(
        "spring.datasource.url",
        () -> "jdbc:postgresql://127.0.0.1:" + DATABASE.port() + "/postgres");
    registry.add("platform.redis.port", REDIS::port);
    registry.add("platform.redis.host", () -> "127.0.0.1");
    registry.add("platform.limits.namespace", () -> NAMESPACE);
  }

  @BeforeEach
  void readyFixture() throws Exception {
    assertThat(((com.zaxxer.hikari.HikariDataSource) webDatabase).getJdbcUrl())
        .contains(":" + DATABASE.port() + "/");
    assertThat(redisSettings.port()).isEqualTo(REDIS.port());

    DATABASE.recover();
    REDIS.recover();
    awaitReady();
  }

  void awaitReady() throws Exception {
    long deadline = System.nanoTime() + Duration.ofSeconds(12).toNanos();
    do {
      readiness.refresh();
      if (readiness.ready()) return;
      Thread.sleep(100);
    } while (System.nanoTime() < deadline);
    throw new AssertionError("Required PostgreSQL/Redis did not recover");
  }

  void verifyUnavailable() throws Exception {
    http.perform(get("/health/ready"))
        .andExpect(status().isServiceUnavailable())
        .andExpect(content().json("{\"status\":\"unavailable\"}"));
    http.perform(get("/health/live")).andExpect(status().isOk());
    assertThat(dependenciesHealth.health().getStatus())
        .isEqualTo(org.springframework.boot.health.contributor.Status.DOWN);
    http.perform(get("/actuator/health/readiness")).andExpect(status().isNotFound());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", "synthetic-outage-key")
                .contentType("application/json")
                .content("{\"input\":\"synthetic\"}"))
        .andExpect(status().isServiceUnavailable())
        .andExpect(header().string("Retry-After", "1"));
  }

  @Test
  void redisNetworkFailureClosesAdmissionButLivenessSurvivesAndReadinessRecovers()
      throws Exception {
    REDIS.disconnect();
    try {
      long started = System.nanoTime();
      readiness.refresh();
      verifyUnavailable();
      assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofSeconds(4));
    } finally {
      REDIS.recover();
      awaitReady();
    }
    http.perform(get("/health/ready")).andExpect(status().isOk());
  }

  @Test
  void databaseNetworkFailureClosesAdmissionButLivenessSurvivesAndReadinessRecovers()
      throws Exception {
    DATABASE.disconnect();
    try {
      long started = System.nanoTime();
      readiness.refresh();
      verifyUnavailable();
      assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofSeconds(4));
    } finally {
      DATABASE.recover();
      awaitReady();
    }
    http.perform(get("/health/ready")).andExpect(status().isOk());
  }

  @Test
  @DirtiesContext
  void drainingRejectsNewWorkAndReadinessWhileKeepingLiveness() throws Exception {
    drain.begin();
    verifyUnavailable();
  }
}
