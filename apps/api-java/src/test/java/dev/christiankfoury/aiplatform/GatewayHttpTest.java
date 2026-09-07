package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.gateway.MockCompletionProvider;
import dev.christiankfoury.aiplatform.persistence.model.*;
import dev.christiankfoury.aiplatform.persistence.repository.*;
import jakarta.persistence.EntityManager;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
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
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest(properties = {"gateway.provider.retry-backoff=0ms", "gateway.provider.timeout=1s"})
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class GatewayHttpTest extends PostgresTestSupport {
  private static final String PROMPT =
      "You are the local mock provider for the Production AI Platform.";
  @Autowired private MockMvc http;
  @Autowired private io.micrometer.core.instrument.MeterRegistry metrics;
  @Autowired private javax.sql.DataSource dataSource;
  @Autowired private JsonMapper json;
  @Autowired private EntityManager entities;
  @Autowired private PlatformTransactionManager transactionManager;
  @Autowired private GatewayRequestRepository requests;
  @Autowired private ApiKeyRepository keys;
  @Autowired private ClientApplicationRepository applications;
  @Autowired private PromptVersionRepository prompts;
  @Autowired private ModelRouteRepository routes;
  @MockitoSpyBean private MockCompletionProvider provider;
  @MockitoSpyBean private CostRecordRepository costs;
  private Project project;
  private ClientApplication application;
  private ApiKey key;
  private PromptVersion prompt;
  private ModelRoute route;
  private String rawKey;

  @DynamicPropertySource
  static void gatewaySchema(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.hikari.schema", () -> "gateway_test");
    registry.add("spring.jpa.properties.hibernate.default_schema", () -> "gateway_test");
    registry.add("spring.flyway.default-schema", () -> "gateway_test");
    registry.add("spring.flyway.schemas", () -> "gateway_test");
  }

  @BeforeEach
  void fixture() {
    rawKey = "gateway-test-placeholder-" + UUID.randomUUID();
    new TransactionTemplate(transactionManager)
        .executeWithoutResult(
            status -> {
              project = new Project();
              project.setName("Synthetic gateway project");
              project.setSlug("test_" + UUID.randomUUID());
              entities.persist(project);
              application = new ClientApplication();
              application.setProjectId(project.getId());
              application.setName("Synthetic client");
              application.setSlug("client");
              entities.persist(application);
              key = new ApiKey();
              key.setApplicationId(application.getId());
              key.setKeyHash(ApplicationAuthenticator.hash(rawKey));
              key.setKeyPrefix("gateway-test");
              entities.persist(key);
              prompt = new PromptVersion();
              prompt.setProjectId(project.getId());
              prompt.setApplicationId(application.getId());
              prompt.setName("default-chat");
              prompt.setVersion(1);
              prompt.setContent(PROMPT);
              entities.persist(prompt);
              route = new ModelRoute();
              route.setProjectId(project.getId());
              route.setApplicationId(application.getId());
              route.setProvider("mock");
              route.setModelName("mock-llm-small");
              route.setIsDefault(true);
              entities.persist(route);
            });
  }

  private ResultActions completion(Map<String, ?> body) throws Exception {
    return http.perform(
        post("/v1/gateway/completions")
            .header("X-API-Key", rawKey)
            .header("X-Request-ID", "contract-http-1")
            .contentType("application/json")
            .content(json.writeValueAsString(body)));
  }

  private long requestCount() {
    return requests.findAll().stream()
        .filter(item -> item.getApplicationId().equals(application.getId()))
        .count();
  }

  @Test
  void successMatchesWireAndStoredContract(CapturedOutput output) throws Exception {
    String response =
        completion(Map.of("input", "synthetic hello"))
            .andExpect(status().isOk())
            .andExpect(header().string("X-Request-ID", "contract-http-1"))
            .andExpect(jsonPath("$.status").value("succeeded"))
            .andExpect(jsonPath("$.provider").value("mock"))
            .andExpect(jsonPath("$.model").value("mock-llm-small"))
            .andExpect(jsonPath("$.prompt_version").value(1))
            .andExpect(jsonPath("$.input_tokens").value(13))
            .andExpect(jsonPath("$.output_tokens").value(16))
            .andExpect(jsonPath("$.estimated_cost_usd").value("0.000005"))
            .andExpect(
                jsonPath("$.output")
                    .value("[mock:mock-llm-small] " + PROMPT + " Input received: synthetic hello"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    String id = json.readTree(response).get("request_id").asString();
    assertThat(id).matches("req_[a-f0-9]{32}");
    var stored =
        requests.findAll().stream()
            .filter(item -> item.getRequestId().equals(id))
            .findFirst()
            .orElseThrow();
    assertThat(stored.getLatencyMs()).isGreaterThanOrEqualTo(1);
    assertThat(stored.getApplicationId()).isEqualTo(application.getId());
    assertThat(stored.getProjectId()).isEqualTo(project.getId());
    assertThat(stored.getApiKeyId()).isEqualTo(key.getId());
    assertThat(stored.getPromptVersionId()).isEqualTo(prompt.getId());
    assertThat(stored.getModelRouteId()).isEqualTo(route.getId());
    assertThat(stored.getExternalMetadataJson()).isNull();
    assertThat(costs.findByGatewayRequestId(stored.getId()).orElseThrow().getEstimatedCostUsd())
        .isEqualByComparingTo("0.000005");
    assertThat(output.getAll()).doesNotContain(rawKey, "synthetic hello", PROMPT);
  }

  @Test
  void missingInvalidInactiveAndRevokedKeysNeverCallProvider() throws Exception {
    http.perform(
            post("/v1/gateway/completions")
                .contentType("application/json")
                .content("{\"input\":\"synthetic\"}"))
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.detail").value("Missing API key"));
    String valid = rawKey;
    rawKey = "invalid-placeholder";
    completion(Map.of("input", "synthetic")).andExpect(status().isUnauthorized());
    rawKey = valid;
    key.setIsActive(false);
    keys.saveAndFlush(key);
    completion(Map.of("input", "synthetic")).andExpect(status().isUnauthorized());
    key.setIsActive(true);
    key.setRevokedAt(OffsetDateTime.now());
    keys.saveAndFlush(key);
    completion(Map.of("input", "synthetic")).andExpect(status().isUnauthorized());
    assertThat(requestCount()).isZero();
    verify(provider, times(0)).complete(any(), anyString(), anyInt());
  }

  @Test
  void inactiveApplicationIsRejected() throws Exception {
    application.setIsActive(false);
    applications.saveAndFlush(application);
    completion(Map.of("input", "synthetic"))
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.detail").value("API key is not attached to an active application"));
    assertThat(requestCount()).isZero();
  }

  @Test
  void missingPromptRouteAndUnsupportedProviderAreSafe() throws Exception {
    completion(Map.of("input", "synthetic", "prompt_name", "missing"))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.detail").value("No active prompt version found"));
    completion(Map.of("input", "synthetic", "environment", "missing"))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.detail").value("No active model route found"));
    route.setProvider("external");
    routes.saveAndFlush(route);
    completion(Map.of("input", "synthetic"))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.detail").value("Unsupported model route"));
    assertThat(requestCount()).isZero();
    verify(provider, times(0)).complete(any(), anyString(), anyInt());
  }

  @Test
  void latestPromptDefaultRouteAndScopeAreRespected() throws Exception {
    new TransactionTemplate(transactionManager)
        .executeWithoutResult(
            status -> {
              PromptVersion latest = new PromptVersion();
              latest.setProjectId(project.getId());
              latest.setApplicationId(application.getId());
              latest.setName("default-chat");
              latest.setVersion(2);
              latest.setContent("Synthetic v2");
              entities.persist(latest);
              PromptVersion inactive = new PromptVersion();
              inactive.setProjectId(project.getId());
              inactive.setApplicationId(application.getId());
              inactive.setName("default-chat");
              inactive.setVersion(3);
              inactive.setContent("Inactive v3");
              inactive.setIsActive(false);
              entities.persist(inactive);
              ModelRoute other = new ModelRoute();
              other.setProjectId(project.getId());
              other.setApplicationId(application.getId());
              other.setProvider("unsupported-nondefault");
              other.setModelName("unsupported");
              other.setPriority(0);
              entities.persist(other);
            });
    completion(Map.of("input", "synthetic"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.prompt_version").value(2))
        .andExpect(
            jsonPath("$.output")
                .value("[mock:mock-llm-small] Synthetic v2 Input received: synthetic"));
    prompt.setIsActive(false);
    prompts.saveAndFlush(prompt);
    // An application with no matching prompt cannot borrow another scope's configuration.
    application = new ClientApplication();
    application.setProjectId(project.getId());
    application.setName("Other synthetic client");
    application.setSlug("other-client");
    application = applications.saveAndFlush(application);
    key.setApplicationId(application.getId());
    keys.saveAndFlush(key);
    completion(Map.of("input", "synthetic")).andExpect(status().isNotFound());
  }

  @Test
  void retriesCreateOneRequestAndOneCost() throws Exception {
    completion(Map.of("input", "[simulate_transient_failure]")).andExpect(status().isOk());
    assertThat(requestCount()).isEqualTo(1);
    verify(provider, times(2)).complete(any(), anyString(), anyInt());
    assertThat(
            costs.findAll().stream()
                .filter(item -> item.getApplicationId().equals(application.getId()))
                .count())
        .isEqualTo(1);
  }

  @Test
  void timeoutAndFailureStayDurableWithoutCost() throws Exception {
    completion(Map.of("input", "[simulate_timeout]"))
        .andExpect(status().isGatewayTimeout())
        .andExpect(jsonPath("$.detail").value("Provider timeout"));
    completion(Map.of("input", "[simulate_failure]"))
        .andExpect(status().isBadGateway())
        .andExpect(jsonPath("$.detail").value("Provider failure"));
    var failures =
        requests.findAll().stream()
            .filter(item -> item.getApplicationId().equals(application.getId()))
            .toList();
    assertThat(failures)
        .hasSize(2)
        .allSatisfy(
            item -> {
              assertThat(item.getStatus()).isEqualTo("failed");
              assertThat(item.getEstimatedCostUsd()).isNull();
              assertThat(costs.findByGatewayRequestId(item.getId())).isEmpty();
            });
    assertThat(failures)
        .extracting(GatewayRequest::getErrorCategory)
        .containsExactlyInAnyOrder("provider_timeout", "provider_error");
  }

  @Test
  void unexpectedProviderDiagnosticIsNotExposed(CapturedOutput output) throws Exception {
    doThrow(new IllegalStateException("synthetic-private-provider-diagnostic"))
        .when(provider)
        .complete(any(), anyString(), anyInt());
    String body =
        completion(Map.of("input", "synthetic-private-input"))
            .andExpect(status().isBadGateway())
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(body + output.getAll())
        .doesNotContain("synthetic-private-provider-diagnostic", "synthetic-private-input", rawKey);
    assertThat(requestCount()).isEqualTo(1);
  }

  @Test
  void failedCostWriteRollsBackTheRequest(CapturedOutput output) throws Exception {
    double before =
        metrics
            .counter(
                "llm_gateway_estimated_cost_usd", "provider", "mock", "model", "mock-llm-small")
            .count();
    doThrow(new IllegalStateException("synthetic-private-cost-diagnostic"))
        .when(costs)
        .saveAndFlush(any(CostRecord.class));
    String body =
        completion(Map.of("input", "synthetic-private-input"))
            .andExpect(status().isInternalServerError())
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(requestCount()).isZero();
    assertThat(
            metrics
                .counter(
                    "llm_gateway_estimated_cost_usd", "provider", "mock", "model", "mock-llm-small")
                .count())
        .isEqualTo(before);
    assertThat(body + output.getAll())
        .doesNotContain("synthetic-private-cost-diagnostic", "synthetic-private-input", rawKey);
  }

  @Test
  void validationIsBoundedAndNeverEchoesInput() throws Exception {
    for (Map<String, ?> body :
        java.util.List.of(
            Map.of("input", ""),
            Map.of("input", "x".repeat(8001)),
            Map.of("input", "synthetic", "prompt_name", "x".repeat(161)),
            Map.of("input", "synthetic", "environment", "x".repeat(41)))) {
      completion(body).andExpect(status().is(422)).andExpect(jsonPath("$.detail").isArray());
    }
    completion(Map.of("input", "synthetic", "extra", "sensitive"))
        .andExpect(status().isBadRequest());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", rawKey)
                .contentType("application/json")
                .content("{\"input\":\"synthetic\",\"prompt_name\":null}"))
        .andExpect(status().is(422));
    String emoji = new String(Character.toChars(0x1f600));
    completion(Map.of("input", emoji.repeat(8000))).andExpect(status().isOk());
    completion(Map.of("input", emoji.repeat(8001))).andExpect(status().is(422));
  }

  @Test
  void providerWaitDoesNotHoldADatabaseConnection() throws Exception {
    doAnswer(
            invocation -> {
              var pool = dataSource.unwrap(com.zaxxer.hikari.HikariDataSource.class);
              assertThat(pool.getHikariPoolMXBean().getActiveConnections()).isZero();
              return invocation.callRealMethod();
            })
        .when(provider)
        .complete(any(), anyString(), anyInt());
    completion(Map.of("input", "synthetic")).andExpect(status().isOk());
  }

  @Test
  void validationLocationsUseTheWireFieldNames() throws Exception {
    completion(Map.of("input", "synthetic", "prompt_name", ""))
        .andExpect(status().is(422))
        .andExpect(jsonPath("$.detail[0].loc[1]").value("prompt_name"));
  }

  @Test
  void numbersAndBooleansCannotBecomeInputText() throws Exception {
    for (Object value : java.util.List.of(42, true, 1.5)) {
      completion(Map.of("input", value)).andExpect(status().isBadRequest());
      completion(Map.of("input", "synthetic", "prompt_name", value))
          .andExpect(status().isBadRequest());
      completion(Map.of("input", "synthetic", "environment", value))
          .andExpect(status().isBadRequest());
    }
    assertThat(requestCount()).isZero();
  }

  @Test
  void unsafeCorrelationHeaderIsReplaced() throws Exception {
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", rawKey)
                .header("X-Request-ID", "contains spaces")
                .contentType("application/json")
                .content("{\"input\":\"synthetic\"}"))
        .andExpect(status().isOk())
        .andExpect(
            header()
                .string("X-Request-ID", org.hamcrest.Matchers.matchesPattern("http_[a-f0-9]{32}")));
  }
}
