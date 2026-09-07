package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.persistence.DevelopmentSeeder;
import dev.christiankfoury.aiplatform.persistence.model.GatewayRequest;
import dev.christiankfoury.aiplatform.persistence.repository.*;
import dev.christiankfoury.aiplatform.telemetry.*;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class TelemetryHttpTest extends PostgresTestSupport {
  @Autowired private MockMvc http;
  @Autowired private JsonMapper json;
  @Autowired private DevelopmentSeeder seeder;
  @Autowired private TelemetryNormalizer normalizer;
  @Autowired private GatewayRequestRepository requests;
  @Autowired private ProjectRepository projects;
  @Autowired private ClientApplicationRepository applications;
  @Autowired private ApiKeyRepository keys;
  @Autowired private MeterRegistry metrics;
  @MockitoSpyBean private CostRecordRepository costs;

  @DynamicPropertySource
  static void telemetrySchema(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.hikari.schema", () -> "telemetry_test");
    registry.add("spring.jpa.properties.hibernate.default_schema", () -> "telemetry_test");
    registry.add("spring.flyway.default-schema", () -> "telemetry_test");
    registry.add("spring.flyway.schemas", () -> "telemetry_test");
  }

  @BeforeEach
  void fixture() {
    seeder.seed();
  }

  static Map<String, Map<String, Object>> fixtures() throws Exception {
    try (var resource =
        TelemetryHttpTest.class.getResourceAsStream("/contracts/telemetry-fixtures.json")) {
      return JsonMapper.builder().build().readValue(resource, new TypeReference<>() {});
    }
  }

  static Stream<Arguments> clientFixtures() throws Exception {
    var combined = new LinkedHashMap<>(fixtures());
    for (String client : List.of("proofbase", "agentops")) {
      try (var resource =
          TelemetryHttpTest.class.getResourceAsStream("/client-captures/" + client + ".json")) {
        Map<String, Object> capture =
            JsonMapper.builder().build().readValue(resource, new TypeReference<>() {});
        @SuppressWarnings("unchecked")
        var events = (Map<String, Map<String, Object>>) capture.get("events");
        events.forEach((name, body) -> combined.put(client + "-capture-" + name, body));
      }
    }
    return combined.entrySet().stream()
        .map(entry -> Arguments.of(entry.getKey(), entry.getValue()));
  }

  private Map<String, Object> event(String name) throws Exception {
    var body = new LinkedHashMap<>(fixtures().get(name));
    body.put("event_id", "test_" + UUID.randomUUID());
    return body;
  }

  private String key(Map<String, Object> body) {
    return body.get("source_app").toString().strip().equalsIgnoreCase("proofbase")
        ? DevelopmentSeeder.PROOFBASE_KEY
        : DevelopmentSeeder.AGENTOPS_KEY;
  }

  private ResultActions submit(Map<String, Object> body) throws Exception {
    return submit(json.writeValueAsString(body), key(body));
  }

  private ResultActions submit(String body, String key) throws Exception {
    return http.perform(
        post("/v1/usage/llm-events")
            .contentType("application/json")
            .header("X-API-Key", key)
            .content(body));
  }

  private GatewayRequest stored(Map<String, Object> body) {
    return requests.findAll().stream()
        .filter(item -> Objects.equals(item.getExternalEventId(), body.get("event_id")))
        .findFirst()
        .orElseThrow();
  }

  private double costCounter(String source, String operation) {
    var counter =
        metrics
            .find("llm_external_telemetry_estimated_cost_usd")
            .tags("source_app", source, "operation_type", operation)
            .counter();
    return counter == null ? 0 : counter.count();
  }

  @ParameterizedTest(name = "{0}")
  @MethodSource("clientFixtures")
  void bothClientFixtureSuitesPersistAndReplay(String name, Map<String, Object> body)
      throws Exception {
    var expected = normalizer.normalize(body);
    submit(body)
        .andExpect(status().isAccepted())
        .andExpect(jsonPath("$.accepted").value(true))
        .andExpect(jsonPath("$.duplicate").value(false))
        .andExpect(jsonPath("$.status").value(expected.text("status")));
    var row = stored(body);
    assertThat(row.getProjectId())
        .isEqualTo(projects.findBySlug(expected.text("source_app")).orElseThrow().getId());
    assertThat(row.getExternalMetadataJson())
        .containsEntry("payload_fingerprint", expected.fingerprint());
    assertThat(row.getCreatedAt().toInstant()).isEqualTo(expected.occurredAt().toInstant());
    assertThat(row.getPromptVersionId()).isNull();
    assertThat(row.getModelRouteId()).isNull();
    var cost = costs.findByGatewayRequestId(row.getId());
    if (expected.cost() == null) assertThat(cost).isEmpty();
    else assertThat(cost.orElseThrow().getEstimatedCostUsd()).isEqualByComparingTo(expected.cost());
    submit(body)
        .andExpect(status().isAccepted())
        .andExpect(jsonPath("$.duplicate").value(true))
        .andExpect(jsonPath("$.request_id").value(row.getRequestId()));
  }

  @Test
  void simultaneousRetriesPersistOneEventAndOneCost() throws Exception {
    var body = event("agentops_step");
    double before = costCounter("agentops", "agent_step");
    CyclicBarrier start = new CyclicBarrier(8);
    try (var pool = Executors.newFixedThreadPool(8)) {
      List<Future<String>> results = new ArrayList<>();
      for (int i = 0; i < 8; i++)
        results.add(
            pool.submit(
                () -> {
                  start.await(5, TimeUnit.SECONDS);
                  return submit(body)
                      .andExpect(status().isAccepted())
                      .andReturn()
                      .getResponse()
                      .getContentAsString();
                }));
      int inserted = 0;
      Set<String> requestIds = new HashSet<>();
      for (var result : results) {
        var response = json.readTree(result.get(15, TimeUnit.SECONDS));
        if (!response.get("duplicate").asBoolean()) inserted++;
        requestIds.add(response.get("request_id").asString());
      }
      assertThat(inserted).isOne();
      assertThat(requestIds).hasSize(1);
    }
    var row = stored(body);
    assertThat(
            requests.findAll().stream()
                .filter(item -> Objects.equals(item.getExternalEventId(), body.get("event_id"))))
        .hasSize(1);
    assertThat(
            costs.findAll().stream().filter(item -> item.getGatewayRequestId().equals(row.getId())))
        .hasSize(1);
    assertThat(costCounter("agentops", "agent_step") - before)
        .isCloseTo(0.000080, org.assertj.core.data.Offset.offset(1e-12));
  }

  @Test
  void conflictingConcurrentPayloadsReturnOneConflict() throws Exception {
    var original = event("proofbase_query");
    var changed = new LinkedHashMap<>(original);
    changed.put("latency_ms", 999);
    CyclicBarrier start = new CyclicBarrier(2);
    try (var pool = Executors.newFixedThreadPool(2)) {
      List<Future<Integer>> results = new ArrayList<>();
      for (var body : List.of(original, changed))
        results.add(
            pool.submit(
                () -> {
                  start.await(5, TimeUnit.SECONDS);
                  return submit(body).andReturn().getResponse().getStatus();
                }));
      assertThat(
              List.of(
                  results.get(0).get(15, TimeUnit.SECONDS),
                  results.get(1).get(15, TimeUnit.SECONDS)))
          .containsExactlyInAnyOrder(202, 409);
    }
  }

  @Test
  void authenticatedSourceBindingCannotBeSpoofed() throws Exception {
    var proofbase = event("proofbase_query");
    String body = json.writeValueAsString(proofbase);
    submit(body, "invalid-placeholder").andExpect(status().isUnauthorized());
    submit(body, DevelopmentSeeder.DEMO_KEY).andExpect(status().isForbidden());
    submit(body, DevelopmentSeeder.AGENTOPS_KEY).andExpect(status().isForbidden());
    proofbase.put("operation_type", "agent_step");
    submit(proofbase).andExpect(status().is(422));
    assertThat(
            requests.findAll().stream()
                .filter(
                    item -> Objects.equals(item.getExternalEventId(), proofbase.get("event_id"))))
        .isEmpty();
  }

  @Test
  void inactiveProjectCannotAcceptTelemetryWithAnOtherwiseActiveKey() throws Exception {
    var body = event("proofbase_query");
    var project = projects.findBySlug("proofbase").orElseThrow();
    try {
      project.setIsActive(false);
      projects.saveAndFlush(project);
      submit(body).andExpect(status().isUnauthorized());
      assertThat(
              requests.findAll().stream()
                  .filter(item -> Objects.equals(item.getExternalEventId(), body.get("event_id"))))
          .isEmpty();
    } finally {
      project.setIsActive(true);
      projects.saveAndFlush(project);
    }
    submit(body).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(false));
  }

  @Test
  void revokedKeyAndInactiveApplicationAreRejected() throws Exception {
    var body = event("agentops_step");
    var key =
        keys.findByKeyHash(
                dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator.hash(key(body)))
            .orElseThrow();
    var application = applications.findById(key.getApplicationId()).orElseThrow();
    try {
      key.setRevokedAt(java.time.OffsetDateTime.now());
      keys.saveAndFlush(key);
      submit(body).andExpect(status().isUnauthorized());
      key.setRevokedAt(null);
      keys.saveAndFlush(key);
      application.setIsActive(false);
      applications.saveAndFlush(application);
      submit(body).andExpect(status().isUnauthorized());
    } finally {
      key.setRevokedAt(null);
      keys.saveAndFlush(key);
      application.setIsActive(true);
      applications.saveAndFlush(application);
    }
  }

  @Test
  void summaryNeverAddsTokensOrCostsAndUnknownCostRemainsNull() throws Exception {
    var body = event("agentops_summary");
    double before = costCounter("agentops", "workflow_summary");
    submit(body).andExpect(status().isAccepted());
    var row = stored(body);
    assertThat(row.getEstimatedCostUsd()).isNull();
    assertThat(row.getEstimatedInputTokens()).isNull();
    assertThat(costs.findByGatewayRequestId(row.getId())).isEmpty();
    for (String field :
        List.of("estimated_cost_usd", "input_tokens", "output_tokens", "total_tokens")) {
      var charged = new LinkedHashMap<>(body);
      charged.put(field, 0);
      submit(charged).andExpect(status().is(422));
    }
    assertThat(costCounter("agentops", "workflow_summary")).isEqualTo(before);
    var missing = event("agentops_step");
    missing.remove("estimated_cost_usd");
    // A client claiming estimated pricing without an amount must still report an unknown cost.
    missing.put("pricing_status", "estimated");
    submit(missing).andExpect(status().isAccepted());
    assertThat(stored(missing).getExternalMetadataJson())
        .containsEntry("pricing_status", "unknown");
    assertThat(costs.findByGatewayRequestId(stored(missing).getId())).isEmpty();
  }

  @Test
  void costFailureRollsBackEventAndCountersAndCanBeRetried() throws Exception {
    var body = event("agentops_step");
    double before = costCounter("agentops", "agent_step");
    doThrow(new IllegalStateException("synthetic-storage-error-not-for-client"))
        .when(costs)
        .saveAndFlush(any());
    submit(body)
        .andExpect(status().isInternalServerError())
        .andExpect(jsonPath("$.detail").value("Internal server error"));
    assertThat(
            requests.findAll().stream()
                .filter(item -> Objects.equals(item.getExternalEventId(), body.get("event_id"))))
        .isEmpty();
    assertThat(costCounter("agentops", "agent_step")).isEqualTo(before);
    org.mockito.Mockito.reset(costs);
    submit(body).andExpect(status().isAccepted()).andExpect(jsonPath("$.duplicate").value(false));
  }

  @Test
  void importedPythonFingerprintReplaysButUnverifiableHistoryConflicts() throws Exception {
    var body = event("proofbase_query");
    submit(body).andExpect(status().isAccepted());
    var row = stored(body);
    // The Python golden encoder is verified independently; preexisting row timestamps/identity stay
    // intact.
    String originalId = row.getRequestId();
    var originalTime = row.getCreatedAt();
    submit(body)
        .andExpect(status().isAccepted())
        .andExpect(jsonPath("$.request_id").value(originalId));
    assertThat(stored(body).getCreatedAt()).isEqualTo(originalTime);
    row.setExternalMetadataJson(Map.of("source_app", "proofbase"));
    requests.saveAndFlush(row);
    submit(body).andExpect(status().isConflict());
  }

  @Test
  void unsafeFieldsAndOversizedBodiesNeverReachStorageOrLogs(CapturedOutput output)
      throws Exception {
    var body = event("agentops_step");
    for (String field :
        List.of(
            "prompt",
            "generated_output",
            "input_json",
            "output_json",
            "tool_arguments",
            "api_key")) {
      var unsafe = new LinkedHashMap<>(body);
      unsafe.put(field, "synthetic-private-content");
      submit(unsafe).andExpect(status().is(422));
      unsafe.remove(field);
      unsafe.put("metadata", Map.of(field, "synthetic-private-content"));
      submit(unsafe).andExpect(status().is(422));
    }
    submit(" ".repeat(TelemetryJson.MAX_BODY_BYTES + 1), key(body)).andExpect(status().is(413));
    submit("{\"event_id\":\"synthetic-private-content\",\"event_id\":\"duplicate\"}", key(body))
        .andExpect(status().is(422));
    assertThat(output.getAll()).doesNotContain("synthetic-private-content", key(body));
  }

  @Test
  void arbitraryErrorAndModelNamesNeverBecomeMetricLabels() throws Exception {
    var body = event("proofbase_stream");
    body.put("error_category", "synthetic-error-" + UUID.randomUUID());
    body.put("model", "synthetic-model-" + UUID.randomUUID());
    submit(body).andExpect(status().isAccepted());
    var tags =
        metrics.getMeters().stream()
            .flatMap(meter -> meter.getId().getTags().stream())
            .map(tag -> tag.getValue())
            .toList();
    assertThat(tags)
        .doesNotContain(
            body.get("error_category").toString(),
            body.get("model").toString(),
            body.get("event_id").toString());
    assertThat(
            metrics
                .find("llm_external_telemetry_errors")
                .tags(
                    "source_app",
                    "proofbase",
                    "operation_type",
                    "rag_query_stream",
                    "error_category",
                    "other")
                .counter())
        .isNotNull();
  }
}
