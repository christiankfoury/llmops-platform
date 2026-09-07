package dev.christiankfoury.aiplatform.telemetry;

import io.micrometer.core.instrument.MeterRegistry;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class TelemetryMetrics {
  private static final Set<String> ERRORS =
      Set.of(
          "auth_failed",
          "attribution_failed",
          "validation_error",
          "payload_too_large",
          "duplicate_conflict",
          "storage_failed",
          "provider_timeout",
          "provider_error",
          "rate_limited",
          "unknown",
          "other");
  private final MeterRegistry registry;

  public TelemetryMetrics(MeterRegistry registry) {
    this.registry = registry;
  }

  public void outcome(TelemetryEvent event, String result, String error) {
    String source =
        event == null ? "unknown" : bounded(event.text("source_app"), TelemetryNormalizer.SOURCES);
    String operation =
        event == null
            ? "unknown"
            : bounded(event.text("operation_type"), TelemetryNormalizer.OPERATIONS);
    registry
        .counter(
            "llm_external_telemetry_events",
            "source_app",
            source,
            "operation_type",
            operation,
            "result",
            bounded(result, Set.of("accepted", "duplicate", "rejected")))
        .increment();
    if (error != null)
      registry
          .counter(
              "llm_external_telemetry_errors",
              "source_app",
              source,
              "operation_type",
              operation,
              "error_category",
              bounded(error, ERRORS))
          .increment();
    if (event == null || !result.equals("accepted")) return;
    if (event.cost() != null)
      registry
          .counter(
              "llm_external_telemetry_estimated_cost_usd",
              "source_app",
              source,
              "operation_type",
              operation)
          .increment(event.cost().doubleValue());
    for (String kind : Set.of("input", "output")) {
      Integer tokens = event.integer(kind + "_tokens");
      if (tokens != null)
        registry
            .counter(
                "llm_external_telemetry_tokens",
                "source_app",
                source,
                "operation_type",
                operation,
                "token_type",
                kind)
            .increment(tokens);
    }
  }

  private static String bounded(String value, Set<String> allowed) {
    return value != null && allowed.contains(value) ? value : "other";
  }
}
