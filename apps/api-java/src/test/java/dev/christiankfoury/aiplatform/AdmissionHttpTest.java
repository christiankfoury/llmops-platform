package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.reliability.*;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

@SpringBootTest
@AutoConfigureMockMvc
@Import(AdmissionHttpTest.Quotas.class)
class AdmissionHttpTest extends OperatorTestSupport {
  @TestConfiguration(proxyBeanMethods = false)
  static class Quotas {
    @Bean
    @Primary
    LimitsSettings fixtureLimits() {
      return new LimitsSettings(
          "admission-" + UUID.randomUUID(), 5, 1, 1, Duration.ofSeconds(60), 2);
    }
  }

  @Autowired StringRedisTemplate redis;
  @Autowired LimitsSettings limits;
  @Autowired AdmissionFilter filter;

  @BeforeEach
  void resetOwnedCounters() {
    // Only three counters in this test context's random namespace; never flush shared Redis.
    redis.delete(
        List.of(
            limits.namespace() + ":global:GATEWAY",
            limits.namespace() + ":global:TELEMETRY",
            limits.namespace() + ":global:OPERATOR"));
  }

  String createKey() throws Exception {
    return (String)
        response(
                create("/v1/admin/applications/" + application.getId() + "/api-keys", Map.of())
                    .andExpect(status().isCreated()))
            .get("api_key");
  }

  @Test
  void randomInvalidKeysConsumeOneBoundedPreAuthCounter() throws Exception {
    var existingKeys = new java.util.HashSet<>(redis.keys(limits.namespace() + ":*"));
    for (int index = 0; index < 5; index++)
      http.perform(
              post("/v1/gateway/completions")
                  .header("X-API-Key", "synthetic-invalid-" + UUID.randomUUID())
                  .contentType("application/json")
                  .content("{\"input\":\"synthetic\"}"))
          .andExpect(status().isUnauthorized());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", "another-invalid-key")
                .contentType("application/json")
                .content("{}"))
        .andExpect(status().isTooManyRequests())
        .andExpect(header().exists("Retry-After"))
        .andExpect(header().exists("X-Request-ID"));
    var createdKeys = new java.util.HashSet<>(redis.keys(limits.namespace() + ":*"));
    createdKeys.removeAll(existingKeys);
    assertThat(createdKeys).containsExactly(limits.namespace() + ":global:GATEWAY");
  }

  @Test
  void gatewayKeyQuotaRejectsBeforeAnotherRequestOrCostIsRecorded() throws Exception {
    String key = createKey();
    var prompt = scopeBody();
    prompt.put("name", "default-chat");
    prompt.put("content", "Synthetic prompt");
    create("/v1/admin/prompt-versions", prompt).andExpect(status().isCreated());
    var route = scopeBody();
    route.put("environment", "local");
    route.put("provider", "mock");
    route.put("model_name", "mock-llm-small");
    route.put("is_default", true);
    create("/v1/admin/model-routes", route).andExpect(status().isCreated());
    for (int status : new int[] {200, 429})
      http.perform(
              post("/v1/gateway/completions")
                  .header("X-API-Key", key)
                  .contentType("application/json")
                  .content("{\"input\":\"synthetic\"}"))
          .andExpect(status().is(status));
    assertThat(
            transaction()
                .<Long>execute(
                    s ->
                        entities
                            .createQuery(
                                "select count(r) from GatewayRequest r where applicationId=:app",
                                Long.class)
                            .setParameter("app", application.getId())
                            .getSingleResult()))
        .isEqualTo(1);
    assertThat(
            transaction()
                .<Long>execute(
                    s ->
                        entities
                            .createQuery(
                                "select count(c) from CostRecord c join GatewayRequest r on c.gatewayRequestId=r.id where r.applicationId=:app",
                                Long.class)
                            .setParameter("app", application.getId())
                            .getSingleResult()))
        .isEqualTo(1);
  }

  @Test
  void authenticatedTelemetryAttemptsAreLimitedEvenWhenPayloadValidationFails() throws Exception {
    String key = createKey();
    for (int status : new int[] {422, 429})
      http.perform(
              post("/v1/usage/llm-events")
                  .header("X-API-Key", key)
                  .contentType("application/json")
                  .content("{}"))
          .andExpect(status().is(status));
  }

  @Test
  void queriesAndDeclaredOrChunkedBodiesAreBoundedBeforeApplicationWork() throws Exception {
    http.perform(get("/v1/usage/summary").queryParam("source_app", "x".repeat(4097)))
        .andExpect(status().is(414));
    http.perform(
            post("/v1/gateway/completions")
                .contentType("application/json")
                .content(new byte[32769]))
        .andExpect(status().is(413));
    var chunked =
        new MockHttpServletRequest("POST", "/v1/usage/llm-events") {
          @Override
          public long getContentLengthLong() {
            return -1;
          }
        };
    chunked.setContent(new byte[32769]);
    var response = new MockHttpServletResponse();
    filter.doFilter(
        chunked,
        response,
        (request, result) -> {
          throw new AssertionError("Oversized body reached application");
        });
    assertThat(response.getStatus()).isEqualTo(413);
  }

  @Test
  void occupiedAdmissionSlotsRejectNewWorkWithoutBlockingHealthChecks() throws Exception {
    CountDownLatch entered = new CountDownLatch(2);
    CountDownLatch release = new CountDownLatch(1);
    try (var workers = Executors.newFixedThreadPool(2)) {
      var tasks = new java.util.ArrayList<java.util.concurrent.Future<?>>();
      try {
        for (int index = 0; index < 2; index++)
          tasks.add(
              workers.submit(
                  () -> {
                    try {
                      filter.doFilter(
                          new MockHttpServletRequest("GET", "/v1/usage/scopes"),
                          new MockHttpServletResponse(),
                          (request, response) -> {
                            entered.countDown();
                            try {
                              if (!release.await(5, TimeUnit.SECONDS))
                                throw new AssertionError("Fixture release missing");
                            } catch (InterruptedException stopped) {
                              Thread.currentThread().interrupt();
                              throw new java.io.IOException(stopped);
                            }
                          });
                    } catch (Exception failure) {
                      throw new IllegalStateException(failure);
                    }
                  }));
        assertThat(entered.await(2, TimeUnit.SECONDS)).isTrue();
        var rejected = new MockHttpServletResponse();
        filter.doFilter(
            new MockHttpServletRequest("GET", "/v1/usage/scopes"),
            rejected,
            (request, response) -> {
              throw new AssertionError("Capacity was exceeded");
            });
        assertThat(rejected.getStatus()).isEqualTo(503);
        http.perform(get("/health/live")).andExpect(status().isOk());
      } finally {
        release.countDown();
      }
      for (var task : tasks) task.get(3, TimeUnit.SECONDS);
    }
  }
}
