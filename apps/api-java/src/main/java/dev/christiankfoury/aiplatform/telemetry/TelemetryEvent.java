package dev.christiankfoury.aiplatform.telemetry;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record TelemetryEvent(
    Map<String, Object> normalized, OffsetDateTime occurredAt, BigDecimal cost) {
  public TelemetryEvent {
    normalized = Collections.unmodifiableMap(new LinkedHashMap<>(normalized));
  }

  public String text(String field) {
    return (String) normalized.get(field);
  }

  public Integer integer(String field) {
    return (Integer) normalized.get(field);
  }

  public String fingerprint() {
    return PythonJson.fingerprint(normalized);
  }

  @Override
  public String toString() {
    return "TelemetryEvent[operational fields omitted]";
  }

  public Map<String, Object> persistedMetadata() {
    Map<String, Object> metadata = new LinkedHashMap<>();
    for (String field :
        List.of(
            "source_app",
            "operation_type",
            "external_request_id",
            "pricing_status",
            "prompt_name",
            "prompt_version",
            "total_tokens",
            "retrieval_latency_ms",
            "generation_latency_ms",
            "error_message_redacted",
            "project_external_id",
            "department_external_id")) {
      Object value = normalized.get(field);
      if (value != null) metadata.put(field, value);
    }
    metadata.put("occurred_at", formatTime(occurredAt, false));
    metadata.put("payload_fingerprint", fingerprint());
    if (normalized.get("metadata") instanceof Map<?, ?> values) {
      for (var entry : values.entrySet())
        if (entry.getValue() != null) metadata.put("metadata." + entry.getKey(), entry.getValue());
    }
    // Keep reporting honest without changing the legacy replay fingerprint representation.
    if (!metadata.containsKey("pricing_status")
        || (cost == null && "estimated".equals(metadata.get("pricing_status"))))
      metadata.put("pricing_status", cost == null ? "unknown" : "estimated");
    return metadata;
  }

  public static String formatTime(OffsetDateTime value, boolean utcAsZ) {
    String text =
        value.format(DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss", java.util.Locale.ROOT));
    if (value.getNano() != 0)
      text += "." + String.format(java.util.Locale.ROOT, "%06d", value.getNano() / 1000);
    String offset = value.getOffset().getId();
    return text + (offset.equals("Z") && !utcAsZ ? "+00:00" : offset);
  }
}
