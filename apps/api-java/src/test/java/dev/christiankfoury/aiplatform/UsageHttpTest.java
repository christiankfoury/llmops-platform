package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.persistence.model.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import tools.jackson.core.type.TypeReference;

@SpringBootTest
@AutoConfigureMockMvc
class UsageHttpTest extends OperatorTestSupport {
  private static final OffsetDateTime TIME = OffsetDateTime.parse("2026-01-02T03:04:05.123456Z");

  private GatewayRequest row(int index, String status, Integer latency, String cost) {
    GatewayRequest row = new GatewayRequest();
    row.setProjectId(project.getId());
    row.setApplicationId(application.getId());
    row.setRequestId("query_" + UUID.randomUUID());
    row.setStatus(status);
    row.setProvider("mock");
    row.setModelName("mock-llm-small");
    row.setLatencyMs(latency);
    row.setCreatedAt(TIME.plusSeconds(index));
    row.setUpdatedAt(TIME.plusSeconds(index));
    if (status.equals("failed")) row.setErrorCategory("provider_timeout");
    if (cost != null) row.setEstimatedCostUsd(new BigDecimal(cost));
    entities.persist(row);
    if (cost != null) {
      CostRecord record = new CostRecord();
      record.setGatewayRequestId(row.getId());
      record.setProjectId(project.getId());
      record.setApplicationId(application.getId());
      record.setProvider("mock");
      record.setModelName("mock-llm-small");
      record.setEstimatedCostUsd(new BigDecimal(cost));
      entities.persist(record);
    }
    return row;
  }

  @Test
  void seededSummaryMatchesReferenceAndKeepsNullAndDecimalContracts() throws Exception {
    transaction()
        .executeWithoutResult(
            status -> {
              row(0, "succeeded", 100, "0.000003");
              row(1, "failed", 50, null);
              var summary = row(2, "succeeded", null, null);
              summary.setSourceApp("agentops");
              summary.setOperationType("workflow_summary");
            });
    var result =
        http.perform(get("/v1/usage/summary").param("project_id", project.getId().toString()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.request_count").value(3))
            .andExpect(jsonPath("$.error_count").value(1))
            .andExpect(jsonPath("$.average_latency_ms").value(75.0))
            .andExpect(jsonPath("$.estimated_cost_usd").value("0.000003"));
    assertThat(response(result).keySet())
        .containsExactlyInAnyOrder(
            "request_count", "error_count", "average_latency_ms", "estimated_cost_usd");
    var rows =
        http.perform(get("/v1/usage/requests").param("project_id", project.getId().toString()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].operation_type").value("workflow_summary"))
            .andExpect(jsonPath("$[0].estimated_cost_usd").isEmpty())
            .andExpect(jsonPath("$[1].error_category").value("provider_timeout"))
            .andExpect(jsonPath("$[2].estimated_cost_usd").value("0.000003"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    List<Map<String, Object>> decoded = json.readValue(rows, new TypeReference<>() {});
    assertThat(decoded.get(2).get("created_at")).isEqualTo("2026-01-02T03:04:05.123456Z");
    assertThat(decoded.getFirst().keySet())
        .containsExactlyInAnyOrder(
            "id",
            "request_id",
            "project_id",
            "project_name",
            "project_slug",
            "application_id",
            "application_name",
            "application_slug",
            "application_environment",
            "prompt_version_id",
            "model_route_id",
            "status",
            "provider",
            "model_name",
            "latency_ms",
            "estimated_input_tokens",
            "estimated_output_tokens",
            "estimated_cost_usd",
            "error_category",
            "source_app",
            "operation_type",
            "external_event_id",
            "external_request_id",
            "created_at");
    assertThat(decoded.getFirst())
        .doesNotContainKeys("api_key_id", "external_metadata_json", "content");
  }

  @Test
  void filtersAreCombinedAndErrorsAlwaysMeanFailed() throws Exception {
    transaction()
        .executeWithoutResult(
            status -> {
              row(0, "succeeded", 100, "0.000003");
              var failure = row(1, "failed", 50, null);
              failure.setSourceApp("proofbase");
              failure.setOperationType("rag_query");
            });
    http.perform(
            get("/v1/usage/errors")
                .param("project_id", project.getId().toString())
                .param("application_id", application.getId().toString())
                .param("status", "succeeded")
                .param("provider", "mock")
                .param("model_name", "mock-llm-small")
                .param("source_app", "proofbase")
                .param("operation_type", "rag_query")
                .param("error_category", "provider_timeout")
                .param("created_from", TIME.plusSeconds(1).toString())
                .param("created_to", TIME.plusSeconds(1).toString()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(1))
        .andExpect(jsonPath("$[0].status").value("failed"));
    http.perform(
            get("/v1/usage/requests")
                .param("project_id", project.getId().toString())
                .param("provider", "mock' OR 1=1 --"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(0));
    http.perform(
            get("/v1/usage/summary")
                .param("project_id", project.getId().toString())
                .param("application_id", UUID.randomUUID().toString()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.request_count").value(0))
        .andExpect(jsonPath("$.average_latency_ms").value(0.0))
        .andExpect(jsonPath("$.estimated_cost_usd").value("0.000000"));
  }

  @Test
  void dateFiltersTruncateExcessPrecisionLikeThePythonReference() throws Exception {
    transaction().executeWithoutResult(status -> row(0, "succeeded", 1, null));
    http.perform(
            get("/v1/usage/requests")
                .param("project_id", project.getId().toString())
                .param("created_from", "2026-01-02T03:04:05.123456999Z")
                .param("created_to", "2026-01-02T03:04:05.123456999Z"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(1));
  }

  @Test
  void limitsAreCappedAndTiesHaveStableOrdering() throws Exception {
    transaction()
        .executeWithoutResult(
            status -> {
              for (int index = 0; index < 105; index++) row(0, "succeeded", null, null);
            });
    var request =
        get("/v1/usage/requests")
            .param("project_id", project.getId().toString())
            .param("limit", "99999999999999999999");
    String first =
        http.perform(request)
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.length()").value(100))
            .andReturn()
            .getResponse()
            .getContentAsString();
    String second =
        http.perform(request)
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(second).isEqualTo(first);
    http.perform(get("/v1/usage/requests").param("project_id", project.getId().toString()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(20));
  }

  @Test
  void activeScopesPreserveEmptyProjectsAndHideInactiveApplications() throws Exception {
    transaction()
        .executeWithoutResult(
            status -> {
              var app = entities.find(ClientApplication.class, application.getId());
              app.setIsActive(false);
            });
    String body =
        http.perform(get("/v1/usage/scopes"))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    List<Map<String, Object>> scopes = json.readValue(body, new TypeReference<>() {});
    var match =
        scopes.stream()
            .filter(item -> item.get("id").equals(project.getId().toString()))
            .findFirst()
            .orElseThrow();
    assertThat(match.keySet()).containsExactlyInAnyOrder("id", "name", "slug", "applications");
    assertThat(match.get("applications")).isEqualTo(List.of());
    transaction()
        .executeWithoutResult(
            status -> entities.find(Project.class, project.getId()).setIsActive(false));
    body =
        http.perform(get("/v1/usage/scopes"))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(body).doesNotContain(project.getId().toString());
  }

  @Test
  void invalidFiltersFailSafely() throws Exception {
    for (var query :
        List.of(
            Map.of("project_id", "1-1-1-1-1"),
            Map.of("limit", "0"),
            Map.of("limit", "-1"),
            Map.of("limit", "1.5"),
            Map.of("provider", "x".repeat(81)),
            Map.of("created_from", "2026-01-02T00:00:00"),
            Map.of("unexpected", "synthetic-private-filter")))
      for (var entry : query.entrySet())
        http.perform(get("/v1/usage/requests").param(entry.getKey(), entry.getValue()))
            .andExpect(status().is(422))
            .andExpect(jsonPath("$.detail[0].msg").value("Invalid value"));
    http.perform(get("/v1/usage/requests").param("status", "failed", "succeeded"))
        .andExpect(status().is(422));
    http.perform(
            get("/v1/usage/requests")
                .param("created_from", TIME.plusDays(1).toString())
                .param("created_to", TIME.toString()))
        .andExpect(status().is(422));
  }

  @Test
  void operatorCredentialsAreRequiredAndBrowserCorsIsClosed() throws Exception {
    http.perform(
            get("/v1/usage/summary")
                .with(
                    org.springframework.security.test.web.servlet.request
                        .SecurityMockMvcRequestPostProcessors.anonymous())
                .header("Cookie", "JSESSIONID=synthetic-cookie")
                .header("X-API-Key", "synthetic-machine-key"))
        .andExpect(status().isUnauthorized());
    http.perform(
            get("/v1/usage/scopes")
                .with(
                    request -> {
                      request.setRemoteAddr("203.0.113.10");
                      return request;
                    }))
        .andExpect(status().isOk());
    http.perform(get("/v1/usage/scopes").header("Origin", "https://untrusted.example.invalid"))
        .andExpect(status().isOk())
        .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
  }
}
