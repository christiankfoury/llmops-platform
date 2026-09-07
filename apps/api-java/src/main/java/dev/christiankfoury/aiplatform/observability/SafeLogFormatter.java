package dev.christiankfoury.aiplatform.observability;

import ch.qos.logback.classic.spi.ILoggingEvent;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Set;
import org.springframework.boot.logging.structured.StructuredLogFormatter;
import tools.jackson.databind.json.JsonMapper;

/** No formatted message, arguments, arbitrary MDC, stack trace, or exception text is exported. */
public final class SafeLogFormatter implements StructuredLogFormatter<ILoggingEvent> {
  private final JsonMapper json = JsonMapper.builder().build();
  private static final Set<String> IDENTIFIERS =
      Set.of("request_id", "gateway_request_id", "project_id", "application_id");
  private static final Set<String> NUMBERS =
      Set.of(
          "status_code",
          "latency_ms",
          "prompt_version",
          "input_tokens",
          "output_tokens",
          "estimated_cost_usd");

  @Override
  public String format(ILoggingEvent event) {
    var out = new LinkedHashMap<String, Object>();
    out.put("timestamp", Instant.ofEpochMilli(event.getTimeStamp()).toString());
    out.put("level", event.getLevel().toString().toLowerCase(Locale.ROOT));
    out.put("component", "api");
    String logger = event.getLoggerName();
    out.put(
        "logger", logger != null && logger.matches("[A-Za-z0-9_.$-]{1,160}") ? logger : "other");
    boolean operational =
        "platform.operations".equals(logger) && "request_completed".equals(event.getMessage());
    out.put("event", operational ? "request_completed" : "framework_event");
    if (operational && event.getKeyValuePairs() != null)
      for (var pair : event.getKeyValuePairs()) {
        String value = pair.value instanceof String text ? text : "";
        if (safe(pair.key, value)) out.put(pair.key, value);
      }
    return json.writeValueAsString(out) + "\n";
  }

  private static boolean safe(String key, String value) {
    if (IDENTIFIERS.contains(key)) return value.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}");
    if (NUMBERS.contains(key)) return value.matches("[0-9]{1,12}(\\.[0-9]{1,6})?");
    if (key.equals("trace_id")) return value.matches("[0-9a-f]{32}");
    if (key.equals("span_id")) return value.matches("[0-9a-f]{16}");
    return switch (key) {
      case "route" -> Set.of("gateway", "telemetry", "operator", "other").contains(value);
      case "method" ->
          Set.of("GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS", "OTHER")
              .contains(value);
      case "provider" -> Set.of("mock", "unknown").contains(value);
      case "model" -> Set.of("mock-llm-small", "unknown").contains(value);
      case "error_category" -> PlatformMetrics.ERRORS.contains(value);
      default -> false;
    };
  }
}
