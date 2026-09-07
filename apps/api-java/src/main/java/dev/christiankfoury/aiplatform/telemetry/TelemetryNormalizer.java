package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.http.ValidationFailure;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class TelemetryNormalizer {
  public static final Set<String> SOURCES = Set.of("proofbase", "agentops");
  public static final Set<String> OPERATIONS =
      Set.of(
          "rag_query",
          "rag_query_stream",
          "markdown_cleanup",
          "query_decomposition",
          "embedding_generation",
          "agent_step",
          "structured_generation",
          "workflow_summary");
  private static final Set<String> METADATA_KEYS =
      Set.of(
          "retrieval_mode",
          "chunking_strategy",
          "top_k",
          "citation_count",
          "response_type",
          "streaming",
          "cache_hit",
          "document_count",
          "chunk_count",
          "embedding_count",
          "question_hash",
          "document_external_id",
          "session_external_id",
          "workflow_external_id",
          "agent_step_external_id",
          "agent_name",
          "agent_type",
          "step_order",
          "retry_count",
          "workflow_status",
          "step_status");
  private static final Set<String> FIELDS =
      Set.of(
          "event_id",
          "external_request_id",
          "source_app",
          "operation_type",
          "environment",
          "occurred_at",
          "status",
          "provider",
          "model",
          "model_name",
          "prompt_name",
          "prompt_version",
          "input_tokens",
          "output_tokens",
          "total_tokens",
          "estimated_cost_usd",
          "currency",
          "pricing_status",
          "latency_ms",
          "retrieval_latency_ms",
          "generation_latency_ms",
          "error_category",
          "error_message_redacted",
          "project_external_id",
          "department_external_id",
          "metadata");
  private static final BigDecimal MAX_COST = new BigDecimal("999999.999999");

  public TelemetryEvent normalize(byte[] body) {
    return normalize(TelemetryJson.decode(body));
  }

  public TelemetryEvent normalize(Map<String, Object> supplied) {
    Map<String, Object> raw = new LinkedHashMap<>(supplied);
    if (!FIELDS.containsAll(raw.keySet())) throw new ValidationFailure(null);
    if (raw.containsKey("model_name")) {
      if (raw.containsKey("model")) throw new ValidationFailure("model");
      raw.put("model", raw.remove("model_name"));
    }
    Map<String, Object> value = new LinkedHashMap<>();
    value.put("event_id", text(raw, "event_id", 1, 80, false));
    value.put("external_request_id", text(raw, "external_request_id", 1, 120, false));
    for (String field : List.of("source_app", "environment", "provider")) {
      String normalized =
          strip(text(raw, field, 1, field.equals("environment") ? 40 : 80, false))
              .toLowerCase(Locale.ROOT);
      if (normalized.isEmpty()) throw new ValidationFailure(field);
      value.put(field, normalized);
    }
    if (!SOURCES.contains(value.get("source_app"))) throw new ValidationFailure("source_app");
    value.put("operation_type", choice(raw, "operation_type", OPERATIONS, false));
    value.put("status", choice(raw, "status", Set.of("succeeded", "failed", "skipped"), false));
    String model = strip(text(raw, "model", 1, 160, false));
    if (model.isEmpty()) throw new ValidationFailure("model");
    value.put("model", model);
    for (var bound :
        Map.of(
                "prompt_name",
                160,
                "prompt_version",
                80,
                "error_category",
                80,
                "error_message_redacted",
                240,
                "project_external_id",
                120,
                "department_external_id",
                120)
            .entrySet()) {
      value.put(bound.getKey(), text(raw, bound.getKey(), 0, bound.getValue(), true));
    }
    if (!raw.containsKey("currency")) raw.put("currency", "USD");
    String currency = strip(text(raw, "currency", 3, 3, false)).toUpperCase(Locale.ROOT);
    if (currency.length() != 3) throw new ValidationFailure("currency");
    value.put("currency", currency);
    value.put(
        "pricing_status",
        choice(raw, "pricing_status", Set.of("estimated", "unpriced", "cached", "unknown"), true));
    for (String field :
        List.of(
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "latency_ms",
            "retrieval_latency_ms",
            "generation_latency_ms")) value.put(field, integer(raw, field));
    Integer input = (Integer) value.get("input_tokens"),
        output = (Integer) value.get("output_tokens"),
        total = (Integer) value.get("total_tokens");
    if (input != null && output != null && total != null && (long) input + output != total)
      throw new ValidationFailure("total_tokens");
    if ("failed".equals(value.get("status"))
        && (value.get("error_category") == null
            || ((String) value.get("error_category")).isBlank()))
      throw new ValidationFailure("error_category");
    OffsetDateTime occurred;
    try {
      occurred =
          OffsetDateTime.parse(text(raw, "occurred_at", 1, 64, false))
              .truncatedTo(ChronoUnit.MICROS);
      if (occurred.getYear() < 1 || occurred.getYear() > 9999)
        throw new ValidationFailure("occurred_at");
    } catch (DateTimeParseException invalid) {
      throw new ValidationFailure("occurred_at");
    }
    value.put("occurred_at", TelemetryEvent.formatTime(occurred, true));
    BigDecimal cost = null;
    String decimal = null;
    Object rawCost = raw.get("estimated_cost_usd");
    if (rawCost != null) {
      try {
        String spelling;
        if (rawCost instanceof String text) spelling = strip(text);
        else if (rawCost instanceof Double number) spelling = PythonJson.floatText(number);
        else if (rawCost instanceof Integer
            || rawCost instanceof Long
            || rawCost instanceof BigInteger) spelling = rawCost.toString();
        else throw new IllegalArgumentException("Expected cost number or string");
        if (spelling.length() > 100)
          throw new IllegalArgumentException("Cost representation too long");
        BigDecimal amount = new BigDecimal(spelling);
        if (Math.abs((long) amount.scale()) > 100 || amount.signum() < 0)
          throw new IllegalArgumentException("Cost outside bounds");
        decimal = (spelling.startsWith("-") && amount.signum() == 0 ? "-" : "") + amount.toString();
        cost = amount.setScale(6, RoundingMode.HALF_EVEN);
        if (cost.compareTo(MAX_COST) > 0) throw new IllegalArgumentException("Cost outside bounds");
      } catch (IllegalArgumentException | ArithmeticException invalid) {
        throw new ValidationFailure("estimated_cost_usd");
      }
      if (!"USD".equals(currency)) throw new ValidationFailure("currency");
    }
    value.put("estimated_cost_usd", decimal);
    if ("workflow_summary".equals(value.get("operation_type"))) {
      if (cost != null || input != null || output != null || total != null)
        throw new ValidationFailure("operation_type");
      if ("estimated".equals(value.get("pricing_status"))
          || "cached".equals(value.get("pricing_status")))
        throw new ValidationFailure("pricing_status");
    }
    Object rawMetadata = raw.getOrDefault("metadata", Map.of());
    if (!(rawMetadata instanceof Map<?, ?> metadata) || metadata.size() > 20)
      throw new ValidationFailure("metadata");
    Map<String, Object> safeMetadata = new LinkedHashMap<>();
    for (var entry : metadata.entrySet()) {
      if (!(entry.getKey() instanceof String key)) throw new ValidationFailure("metadata");
      String normalized = strip(key).toLowerCase(Locale.ROOT);
      if (!METADATA_KEYS.contains(normalized)) throw new ValidationFailure("metadata");
      Object item = entry.getValue();
      if (item instanceof String text) validateText(text, "metadata", 0, 240);
      else if (item instanceof Number number) {
        if (!Double.isFinite(number.doubleValue()) || Math.abs(number.doubleValue()) > 1e12)
          throw new ValidationFailure("metadata");
      } else if (item != null && !(item instanceof Boolean))
        throw new ValidationFailure("metadata");
      safeMetadata.put(normalized, item);
    }
    if (PythonJson.encode(safeMetadata).length() > 2048) throw new ValidationFailure("metadata");
    value.put("metadata", Collections.unmodifiableMap(safeMetadata));
    return new TelemetryEvent(value, occurred, cost);
  }

  private static Integer integer(Map<String, Object> raw, String field) {
    Object value = raw.get(field);
    if (value == null) return null;
    if (!(value instanceof Integer || value instanceof Long || value instanceof BigInteger))
      throw new ValidationFailure(field);
    BigInteger number = new BigInteger(value.toString());
    if (number.signum() < 0 || number.compareTo(BigInteger.valueOf(Integer.MAX_VALUE)) > 0)
      throw new ValidationFailure(field);
    return number.intValueExact();
  }

  private static String choice(
      Map<String, Object> raw, String field, Set<String> allowed, boolean optional) {
    String value = text(raw, field, 1, 80, optional);
    if (value != null && !allowed.contains(value)) throw new ValidationFailure(field);
    return value;
  }

  private static String text(
      Map<String, Object> raw, String field, int min, int max, boolean optional) {
    Object value = raw.get(field);
    if (value == null && optional) return null;
    if (!(value instanceof String text)) throw new ValidationFailure(field);
    validateText(text, field, min, max);
    return text;
  }

  private static void validateText(String value, String field, int min, int max) {
    int length = value.codePointCount(0, value.length());
    if (length < min || length > max || value.indexOf(0) >= 0) throw new ValidationFailure(field);
    for (int index = 0; index < value.length(); index++) {
      char c = value.charAt(index);
      if (Character.isHighSurrogate(c)) {
        if (index + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(++index)))
          throw new ValidationFailure(field);
      } else if (Character.isLowSurrogate(c)) throw new ValidationFailure(field);
    }
  }

  private static String strip(String value) {
    int start = 0, end = value.length();
    while (start < end && whitespace(value.codePointAt(start)))
      start += Character.charCount(value.codePointAt(start));
    while (end > start && whitespace(value.codePointBefore(end)))
      end -= Character.charCount(value.codePointBefore(end));
    return value.substring(start, end);
  }

  private static boolean whitespace(int point) {
    return Character.isWhitespace(point) || Character.isSpaceChar(point) || point == 0x85;
  }
}
