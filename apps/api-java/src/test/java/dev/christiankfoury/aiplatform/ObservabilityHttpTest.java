package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;

import dev.christiankfoury.aiplatform.reliability.DependencyReadiness;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.testing.exporter.InMemorySpanExporter;
import io.opentelemetry.sdk.trace.data.SpanData;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.system.*;
import org.springframework.boot.test.web.server.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = {
      "management.server.port=0",
      "platform.seed.enabled=true",
      "platform.observability.sample-probability=1"
    })
@Import(ObservabilityHttpTest.Exporter.class)
@ExtendWith(OutputCaptureExtension.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class ObservabilityHttpTest extends PostgresTestSupport {
  private static final TcpFaultProxy REDIS =
      new TcpFaultProxy(
          System.getenv().getOrDefault("TEST_REDIS_HOST", "127.0.0.1"),
          Integer.parseInt(System.getenv().getOrDefault("TEST_REDIS_PORT", "56379")));

  @BeforeEach
  void healthyFixture() throws Exception {
    REDIS.recover();
    awaitReady(true);
  }

  private void awaitReady(boolean expected) throws Exception {
    long deadline = System.nanoTime() + Duration.ofSeconds(8).toNanos();
    while (readiness.ready() != expected && System.nanoTime() < deadline) Thread.sleep(100);
    assertThat(readiness.ready()).as("Real Redis dependency readiness").isEqualTo(expected);
  }

  @TestConfiguration
  static class Exporter {
    @Bean
    @org.springframework.context.annotation.Primary
    dev.christiankfoury.aiplatform.reliability.RedisSettings networkFaultRedis() {
      return new dev.christiankfoury.aiplatform.reliability.RedisSettings(
          "127.0.0.1", REDIS.port(), "", "", false, "local");
    }

    @Bean
    InMemorySpanExporter spanExporter() {
      return InMemorySpanExporter.create();
    }
  }

  @DynamicPropertySource
  static void schema(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.hikari.schema", () -> "observability_test");
    registry.add("spring.jpa.properties.hibernate.default_schema", () -> "observability_test");
    registry.add("spring.flyway.default-schema", () -> "observability_test");
    registry.add("spring.flyway.schemas", () -> "observability_test");
  }

  @LocalServerPort int applicationPort;
  @LocalManagementPort int managementPort;
  @Autowired InMemorySpanExporter exporter;
  @Autowired OpenTelemetrySdk sdk;
  @Autowired DependencyReadiness readiness;
  private final JsonMapper json = JsonMapper.builder().build();
  private static final String KEY = "local-dev-placeholder-key-not-a-secret";
  private static final String TRACE = "4bf92f3577b34da6a3ce929d0e0e4736";

  private HttpResponse<String> request(
      int port, String path, String body, String key, String parent) throws Exception {
    try (var client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build()) {
      var request =
          HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path))
              .timeout(Duration.ofSeconds(5));
      if (body != null)
        request
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body));
      if (key != null) request.header("X-API-Key", key);
      if (parent != null) request.header("traceparent", parent);
      request
          .header("X-Request-ID", "observe-safe-id")
          .header("baggage", "sensitive-baggage-sentinel");
      return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
  }

  private List<SpanData> spans(String id) throws Exception {
    for (int retry = 0; retry < 60; retry++) {
      sdk.getSdkTracerProvider().forceFlush().join(1, java.util.concurrent.TimeUnit.SECONDS);
      var result =
          exporter.getFinishedSpanItems().stream()
              .filter(span -> span.getTraceId().equals(id))
              .toList();
      if (result.stream().anyMatch(span -> span.getName().equals("http.gateway"))) return result;
      Thread.sleep(50);
    }
    throw new AssertionError("HTTP trace was not exported");
  }

  @Test
  void gatewayCorrelatesEveryStageWithoutPayloadsAndMatchesDashboardMetrics(CapturedOutput output)
      throws Exception {
    var response =
        request(
            applicationPort,
            "/v1/gateway/completions?private=secret-query-sentinel",
            "{\"input\":\"secret-prompt-sentinel\"}",
            KEY,
            "00-" + TRACE + "-00f067aa0ba902b7-01");
    assertThat(response.statusCode()).isEqualTo(200);
    assertThat(response.headers().firstValue("X-Trace-ID")).contains(TRACE);
    var traces = spans(TRACE);
    assertThat(traces)
        .extracting(SpanData::getName)
        .containsExactlyInAnyOrder(
            "http.gateway",
            "gateway.authentication",
            "gateway.prompt.lookup",
            "gateway.model.routing",
            "gateway.provider.call",
            "gateway.database.write",
            "http.response.write");
    var server =
        traces.stream()
            .filter(span -> span.getName().equals("http.gateway"))
            .findFirst()
            .orElseThrow();
    assertThat(server.getParentSpanId()).isEqualTo("00f067aa0ba902b7");
    assertThat(traces.stream().filter(span -> !span.equals(server)))
        .allSatisfy(
            span -> {
              assertThat(span.getParentSpanId()).isEqualTo(server.getSpanId());
              assertThat(span.getEvents()).isEmpty();
            });
    String exported = traces.toString();
    assertThat(exported)
        .doesNotContain(
            KEY, "secret-prompt-sentinel", "secret-query-sentinel", "sensitive-baggage-sentinel");
    String log = output.getAll();
    assertThat(log)
        .contains(
            "\"trace_id\":\"" + TRACE,
            "\"request_id\":\"observe-safe-id\"",
            "\"gateway_request_id\":\""
                + json.readTree(response.body()).get("request_id").asString());
    assertThat(log)
        .doesNotContain(
            KEY, "secret-prompt-sentinel", "secret-query-sentinel", "sensitive-baggage-sentinel");
    // Populate the failure/auth/rate families as well as success/cost/token histograms.
    request(
        applicationPort,
        "/v1/gateway/completions",
        "{\"input\":\"[simulate_failure]\"}",
        KEY,
        null);
    request(
        applicationPort,
        "/v1/gateway/completions",
        "{\"input\":\"synthetic\"}",
        "invalid-synthetic-key",
        null);
    var metrics = request(managementPort, "/actuator/prometheus", null, null, null);
    assertThat(metrics.statusCode()).isEqualTo(200);
    assertThat(metrics.body())
        .contains(
            "llm_gateway_requests_total",
            "llm_gateway_errors_total",
            "llm_gateway_request_duration_seconds_bucket",
            "http_request_duration_seconds_bucket",
            "llm_gateway_estimated_cost_usd_total",
            "llm_gateway_tokens_total",
            "llm_gateway_model_routing_total",
            "llm_gateway_api_key_auth_failures_total",
            "platform_dependency_up{dependency=\"redis\"} 1.0");
    assertThat(metrics.body())
        .doesNotContain(
            "observe-safe-id",
            TRACE,
            "secret-query-sentinel",
            KEY,
            "application_id=",
            "project_id=");
    Path root = Path.of("").toAbsolutePath();
    for (int parents = 0;
        !Files.isDirectory(root.resolve("infra/monitoring")) && parents < 3;
        parents++) root = root.getParent();
    for (String dashboard :
        List.of(
            "ai-platform-overview.json", "ai-platform-cost.json", "ai-platform-reliability.json")) {
      String document =
          Files.readString(root.resolve("infra/monitoring/grafana/dashboards/" + dashboard));
      var names =
          java.util.regex.Pattern.compile("(?:llm_gateway|http_)[a-z_]+(?:_total|_bucket)")
              .matcher(document);
      while (names.find()) {
        String name = names.group();
        // Rejections have a separate dedicated test below; its zero meter is initialized at
        // startup.
        assertThat(metrics.body()).as("dashboard metric %s", name).contains(name);
      }
    }
  }

  @Test
  void managementListenerIsSeparateAndReadinessDoesNotBreakLiveness() throws Exception {
    assertThat(managementPort).isNotEqualTo(applicationPort);
    assertThat(request(managementPort, "/v1/gateway/completions", "{}", KEY, null).statusCode())
        .isEqualTo(404);
    for (String path :
        List.of("/actuator/health", "/actuator/prometheus", "/actuator/env", "/actuator/heapdump"))
      assertThat(request(applicationPort, path, null, null, null).statusCode()).isEqualTo(404);
    for (String path :
        List.of(
            "/actuator/env", "/actuator/heapdump", "/actuator/configprops", "/actuator/loggers"))
      assertThat(request(managementPort, path, null, null, null).statusCode()).isEqualTo(404);
    assertThat(request(managementPort, "/actuator/health/readiness", null, null, null).statusCode())
        .isEqualTo(200);
    try {
      REDIS.disconnect();
      awaitReady(false);
      assertThat(
              request(managementPort, "/actuator/health/readiness", null, null, null).statusCode())
          .isEqualTo(503);
      var live = request(managementPort, "/actuator/health/liveness", null, null, null);
      assertThat(live.statusCode()).isEqualTo(200);
      assertThat(live.body()).isEqualTo("{\"status\":\"UP\"}");
    } finally {
      REDIS.recover();
      awaitReady(true);
    }
  }

  @Test
  void invalidParentUnknownPathsAndFailureContentNeverBecomeLabelsOrSpans(CapturedOutput output)
      throws Exception {
    var response =
        request(
            applicationPort,
            "/v1/gateway/completions",
            "{secret-body-sentinel",
            "secret-key-sentinel",
            "secret-parent-sentinel");
    assertThat(response.statusCode()).isEqualTo(400);
    String id = response.headers().firstValue("X-Trace-ID").orElseThrow();
    assertThat(id).matches("[0-9a-f]{32}");
    var traces = spans(id);
    assertThat(
            traces.stream()
                .filter(span -> span.getName().equals("http.gateway"))
                .findFirst()
                .orElseThrow()
                .getParentSpanId())
        .isEqualTo("0000000000000000");
    assertThat(traces).allSatisfy(span -> assertThat(span.getEvents()).isEmpty());
    for (int index = 0; index < 15; index++)
      request(applicationPort, "/v1/unknown-" + index + "-secret-path-sentinel", null, null, null);
    String metrics = request(managementPort, "/actuator/prometheus", null, null, null).body();
    assertThat(metrics).doesNotContain("secret-", id).contains("route=\"other\"");
    assertThat(output.getAll())
        .doesNotContain(
            "secret-body-sentinel",
            "secret-key-sentinel",
            "secret-parent-sentinel",
            "secret-path-sentinel");
    assertThat(traces.toString()).doesNotContain("secret-");
  }
}
