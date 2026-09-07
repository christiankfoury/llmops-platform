package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import jakarta.servlet.RequestDispatcher;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.availability.AvailabilityChangeEvent;
import org.springframework.boot.availability.ReadinessState;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(FoundationTest.TestRoutes.class)
class FoundationTest extends PostgresTestSupport {
  @Autowired private MockMvc mvc;
  @Autowired private JsonMapper mapper;
  @Autowired private ApplicationContext context;

  @Test
  void healthAndOperationalExposure() throws Exception {
    mvc.perform(get("/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.service").value("api"));
    mvc.perform(get("/health/live")).andExpect(status().isOk());
    mvc.perform(get("/health/ready")).andExpect(status().isOk());
    mvc.perform(get("/actuator/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.components").doesNotExist());
    for (String endpoint :
        new String[] {"env", "configprops", "heapdump", "loggers", "mappings", "shutdown"}) {
      mvc.perform(get("/actuator/" + endpoint)).andExpect(status().isNotFound());
    }
  }

  @Test
  void refusingTrafficDoesNotFailLiveness() throws Exception {
    AvailabilityChangeEvent.publish(context, ReadinessState.REFUSING_TRAFFIC);
    try {
      mvc.perform(get("/health/ready")).andExpect(status().isServiceUnavailable());
      mvc.perform(get("/health/live")).andExpect(status().isOk());
    } finally {
      AvailabilityChangeEvent.publish(context, ReadinessState.ACCEPTING_TRAFFIC);
    }
  }

  @Test
  void jsonPreservesDecimalStringsNullsAndDates() throws Exception {
    record Value(BigDecimal estimatedCostUsd, OffsetDateTime occurredAt, String optionalValue) {}
    Value value =
        new Value(
            new BigDecimal("0.000072"), OffsetDateTime.parse("2026-01-02T03:04:05.123456Z"), null);
    String encoded = mapper.writeValueAsString(value);
    var tree = mapper.readTree(encoded);
    assertThat(tree.get("estimated_cost_usd").stringValue()).isEqualTo("0.000072");
    assertThat(tree.get("optional_value").isNull()).isTrue();
    assertThat(OffsetDateTime.parse(tree.get("occurred_at").stringValue()))
        .isEqualTo(value.occurredAt());
    assertThat(mapper.readValue(encoded, Value.class)).isEqualTo(value);
  }

  @Test
  void invalidBodiesAndUnexpectedExceptionsDoNotEchoInput() throws Exception {
    mvc.perform(
            post("/contract-test/validate")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"\"}"))
        .andExpect(status().is(422))
        .andExpect(jsonPath("$.detail[0].loc[1]").value("name"))
        .andExpect(jsonPath("$.detail[0].input").doesNotExist());
    for (String body :
        new String[] {"{secret-sentinel", "{\"name\":\"valid\",\"secret-sentinel\":true}"}) {
      var response =
          mvc.perform(
                  post("/contract-test/validate")
                      .contentType(MediaType.APPLICATION_JSON)
                      .content(body))
              .andExpect(status().isBadRequest())
              .andReturn()
              .getResponse();
      assertThat(response.getContentAsString()).doesNotContain("secret-sentinel");
    }
    var failure =
        mvc.perform(get("/contract-test/fail"))
            .andExpect(status().isInternalServerError())
            .andExpect(jsonPath("$.detail").value("Internal server error"))
            .andReturn()
            .getResponse();
    assertThat(failure.getContentAsString())
        .doesNotContain("secret-sentinel", "IllegalStateException");
  }

  @Test
  void servletFallbackErrorsHideExceptionMessageAndPath() throws Exception {
    mvc.perform(
            get("/error")
                .accept(MediaType.APPLICATION_JSON)
                .requestAttr(RequestDispatcher.ERROR_STATUS_CODE, 500)
                .requestAttr(RequestDispatcher.ERROR_REQUEST_URI, "/secret-sentinel")
                .requestAttr(RequestDispatcher.ERROR_MESSAGE, "secret-sentinel")
                .requestAttr(
                    RequestDispatcher.ERROR_EXCEPTION,
                    new IllegalStateException("secret-sentinel")))
        .andExpect(status().isInternalServerError())
        .andExpect(jsonPath("$.message").doesNotExist())
        .andExpect(jsonPath("$.path").doesNotExist())
        .andExpect(jsonPath("$.exception").doesNotExist())
        .andExpect(jsonPath("$.trace").doesNotExist());
  }

  @RestController
  static class TestRoutes {
    record Payload(@NotBlank String name) {}

    @PostMapping("/contract-test/validate")
    Map<String, String> validate(@Valid @RequestBody Payload payload) {
      return Map.of("name", payload.name());
    }

    @GetMapping("/contract-test/fail")
    String fail() {
      throw new IllegalStateException("secret-sentinel");
    }
  }
}
