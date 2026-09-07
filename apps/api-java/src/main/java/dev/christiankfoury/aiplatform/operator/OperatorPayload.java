package dev.christiankfoury.aiplatform.operator;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.math.BigInteger;
import java.util.Map;
import java.util.Set;
import tools.jackson.core.JacksonException;
import tools.jackson.core.StreamReadConstraints;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.core.json.JsonFactory;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.json.JsonMapper;

public final class OperatorPayload {
  public enum Kind {
    PROMPT_CREATE,
    PROMPT_UPDATE,
    ROUTE_CREATE,
    ROUTE_UPDATE
  }

  public static final int MAX_BYTES = 262144;
  private static final JsonMapper JSON =
      JsonMapper.builder(
              JsonFactory.builder()
                  .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
                  .streamReadConstraints(
                      StreamReadConstraints.builder()
                          .maxNestingDepth(2)
                          .maxStringLength(65536)
                          .maxNumberLength(30)
                          .build())
                  .build())
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .build();
  private static final Map<String, Integer> TEXT =
      Map.of(
          "project_slug",
          120,
          "application_slug",
          120,
          "name",
          160,
          "content",
          32000,
          "environment",
          40,
          "provider",
          80,
          "model_name",
          160);
  private final Map<String, Object> values;

  private OperatorPayload(Map<String, Object> values, Kind kind) {
    this.values = values;
    boolean create = kind == Kind.PROMPT_CREATE || kind == Kind.ROUTE_CREATE;
    Set<String> fields =
        switch (kind) {
          case PROMPT_CREATE ->
              Set.of("project_slug", "application_slug", "name", "content", "version", "is_active");
          case PROMPT_UPDATE -> Set.of("content", "is_active");
          case ROUTE_CREATE ->
              Set.of(
                  "project_slug",
                  "application_slug",
                  "environment",
                  "provider",
                  "model_name",
                  "priority",
                  "is_default",
                  "is_active");
          case ROUTE_UPDATE ->
              Set.of("provider", "model_name", "priority", "is_default", "is_active");
        };
    if (!fields.containsAll(values.keySet())) throw invalid(null);
    for (var entry : values.entrySet()) {
      String name = entry.getKey();
      Object value = entry.getValue();
      if (value == null) {
        if (create && !name.equals("version")) throw invalid(name);
        continue;
      }
      if (TEXT.containsKey(name)) {
        if (!(value instanceof String text)) throw invalid(name);
        validateText(text, name, TEXT.get(name));
      } else if (name.startsWith("is_")) {
        if (!(value instanceof Boolean)) throw invalid(name);
      } else {
        if (!(value instanceof Integer || value instanceof Long || value instanceof BigInteger))
          throw invalid(name);
        BigInteger number = new BigInteger(value.toString());
        if (number.signum() <= 0 || number.compareTo(BigInteger.valueOf(Integer.MAX_VALUE)) > 0)
          throw invalid(name);
      }
    }
    if (create) {
      for (String field : Set.of("project_slug", "application_slug")) required(field);
      if (kind == Kind.PROMPT_CREATE) {
        required("name");
        required("content");
      } else required("model_name");
    }
  }

  public static OperatorPayload read(HttpServletRequest request, Kind kind) throws IOException {
    byte[] bytes = request.getInputStream().readNBytes(MAX_BYTES + 1);
    if (bytes.length > MAX_BYTES) throw new ApiFailure(413, "Operator payload too large");
    try {
      Map<String, Object> value = JSON.readValue(bytes, new TypeReference<>() {});
      if (value == null) throw invalid(null);
      return new OperatorPayload(value, kind);
    } catch (JacksonException failure) {
      throw invalid(null);
    }
  }

  public String text(String field) {
    return (String) values.get(field);
  }

  public String text(String field, String fallback) {
    return values.containsKey(field) ? text(field) : fallback;
  }

  public Boolean flag(String field) {
    return (Boolean) values.get(field);
  }

  public boolean flag(String field, boolean fallback) {
    return values.containsKey(field) ? flag(field) : fallback;
  }

  public Integer integer(String field) {
    return values.get(field) == null ? null : ((Number) values.get(field)).intValue();
  }

  public int integer(String field, int fallback) {
    return values.containsKey(field) ? integer(field) : fallback;
  }

  private void required(String field) {
    if (values.get(field) == null) throw invalid(field);
  }

  private static void validateText(String value, String field, int maximum) {
    int size = value.codePointCount(0, value.length());
    if (size < 1 || size > maximum || value.indexOf(0) >= 0) throw invalid(field);
    for (int index = 0; index < value.length(); index++) {
      char current = value.charAt(index);
      if (Character.isHighSurrogate(current)) {
        if (index + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(++index)))
          throw invalid(field);
      } else if (Character.isLowSurrogate(current)) throw invalid(field);
    }
  }

  private static OperatorValidationFailure invalid(String field) {
    return new OperatorValidationFailure("body", field);
  }

  @Override
  public String toString() {
    return "OperatorPayload[values omitted]";
  }
}
