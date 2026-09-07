package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.http.ValidationFailure;
import dev.christiankfoury.aiplatform.telemetry.PythonJson;
import dev.christiankfoury.aiplatform.telemetry.TelemetryJson;
import dev.christiankfoury.aiplatform.telemetry.TelemetryNormalizer;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

class TelemetryNormalizationTest {
  private static final JsonMapper JSON = JsonMapper.builder().build();
  private static final Map<String, Map<String, Object>> FIXTURES =
      load("telemetry-fixtures.json", new TypeReference<>() {});
  private static final Map<String, Map<String, Object>> GOLDEN =
      load("telemetry-golden.json", new TypeReference<>() {});
  private final TelemetryNormalizer normalizer = new TelemetryNormalizer();

  record JsonVector(Object value, String encoded) {}

  static Stream<String> fixtures() {
    return FIXTURES.keySet().stream().sorted();
  }

  static Stream<JsonVector> jsonVectors() {
    return load("python-json-vectors.json", new TypeReference<List<JsonVector>>() {}).stream();
  }

  @ParameterizedTest
  @MethodSource("fixtures")
  void matchesFrozenPythonNormalizationFingerprintAndStoredFields(String name) {
    var event =
        normalizer.normalize(TelemetryJson.decode(JSON.writeValueAsBytes(FIXTURES.get(name))));
    var expected = GOLDEN.get(name);
    assertThat(event.normalized()).isEqualTo(expected.get("normalized"));
    assertThat(event.fingerprint()).isEqualTo(expected.get("fingerprint"));
    assertThat(event.persistedMetadata()).isEqualTo(expected.get("persisted_metadata"));
    assertThat(event.cost() == null ? null : event.cost().toPlainString())
        .isEqualTo(expected.get("persisted_cost"));
  }

  @ParameterizedTest
  @MethodSource("jsonVectors")
  void matchesPythonAsciiAndFloatRepresentation(JsonVector vector) {
    assertThat(PythonJson.encode(vector.value())).isEqualTo(vector.encoded());
  }

  @Test
  void rejectsDuplicateKeysTrailingDocumentsAndOversizedBodies() {
    for (String body : List.of("{\"event_id\":1,\"event_id\":2}", "{}{}", "null", "[]")) {
      assertThatThrownBy(() -> TelemetryJson.decode(body.getBytes(StandardCharsets.UTF_8)))
          .isInstanceOf(ValidationFailure.class);
    }
    assertThatThrownBy(() -> TelemetryJson.decode(new byte[TelemetryJson.MAX_BODY_BYTES + 1]))
        .isInstanceOfSatisfying(
            ApiFailure.class, failure -> assertThat(failure.status()).isEqualTo(413));
  }

  @Test
  void rejectsSensitiveFieldsNestedMetadataAndNumericOverflow() {
    for (String field :
        List.of(
            "prompt",
            "generated_output",
            "input_json",
            "tool_arguments",
            "provider_payload",
            "api_key")) {
      var raw = valid();
      raw.put(field, "synthetic-private");
      assertThatThrownBy(() -> normalizer.normalize(raw)).isInstanceOf(ValidationFailure.class);
    }
    for (Object metadata :
        List.of(
            Map.of("prompt_text", "synthetic-private"),
            Map.of("tool_results", "synthetic-private"),
            Map.of("retry_count", List.of(1)),
            Map.of("agent_name", "x".repeat(241)),
            Map.of("top_k", Double.POSITIVE_INFINITY),
            Map.of("top_k", 1e13))) {
      var raw = valid();
      raw.put("metadata", metadata);
      assertThatThrownBy(() -> normalizer.normalize(raw)).isInstanceOf(ValidationFailure.class);
    }
    for (Object number : List.of(-1, 2147483648L, true, 3.0, "3")) {
      var raw = valid();
      raw.put("input_tokens", number);
      assertThatThrownBy(() -> normalizer.normalize(raw)).isInstanceOf(ValidationFailure.class);
    }
    for (String amount :
        List.of("NaN", "Infinity", "-0.01", "1000000", "999999.9999999", "1e-1000")) {
      var raw = valid();
      raw.put("estimated_cost_usd", amount);
      assertThatThrownBy(() -> normalizer.normalize(raw)).isInstanceOf(ValidationFailure.class);
    }
  }

  @Test
  void enforcesTimezoneCurrencyTotalsAndSummaryCostRules() {
    for (var replacement :
        List.of(
            Map.entry("occurred_at", (Object) "2026-01-02T03:04:05"),
            Map.entry("currency", (Object) "EUR"),
            Map.entry("total_tokens", (Object) 999),
            Map.entry("source_app", (Object) "   "))) {
      var raw = valid();
      raw.put(replacement.getKey(), replacement.getValue());
      assertThatThrownBy(() -> normalizer.normalize(raw)).isInstanceOf(ValidationFailure.class);
    }
    var nullCurrency = valid();
    nullCurrency.put("currency", null);
    assertThatThrownBy(() -> normalizer.normalize(nullCurrency))
        .isInstanceOf(ValidationFailure.class);
    var brokenText = valid();
    brokenText.put("event_id", String.valueOf((char) 0xd800));
    assertThatThrownBy(() -> normalizer.normalize(brokenText))
        .isInstanceOf(ValidationFailure.class);
    for (String field :
        List.of("estimated_cost_usd", "input_tokens", "output_tokens", "total_tokens")) {
      var summary = new LinkedHashMap<>(FIXTURES.get("agentops_summary"));
      summary.put(field, 0);
      assertThatThrownBy(() -> normalizer.normalize(summary)).isInstanceOf(ValidationFailure.class);
    }
  }

  @Test
  void preservesDecimalScaleNegativeZeroAndMicrosecondOffset() {
    var raw = valid();
    raw.put("estimated_cost_usd", "-0.00");
    assertThat(normalizer.normalize(raw).normalized().get("estimated_cost_usd")).isEqualTo("-0.00");
    raw.put("estimated_cost_usd", "0.0000005");
    assertThat(normalizer.normalize(raw).cost().toPlainString()).isEqualTo("0.000000");
    raw.put("estimated_cost_usd", "0.0000015");
    assertThat(normalizer.normalize(raw).cost().toPlainString()).isEqualTo("0.000002");
    raw.put("occurred_at", "2026-01-02T03:04:05.123000999+05:30");
    assertThat(normalizer.normalize(raw).normalized().get("occurred_at"))
        .isEqualTo("2026-01-02T03:04:05.123000+05:30");
  }

  private static Map<String, Object> valid() {
    return new LinkedHashMap<>(FIXTURES.get("proofbase_query"));
  }

  private static <T> T load(String name, TypeReference<T> type) {
    try (var input = TelemetryNormalizationTest.class.getResourceAsStream("/contracts/" + name)) {
      if (input == null) throw new IllegalStateException("Required compatibility fixture missing");
      return JSON.readValue(input, type);
    } catch (IOException exception) {
      throw new IllegalStateException("Could not load fixture", exception);
    }
  }
}
