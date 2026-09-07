package dev.christiankfoury.aiplatform.observability;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;
import io.micrometer.core.instrument.Timer;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

@Component
public class PlatformMetrics {
  public static final Set<String> ERRORS =
      Set.of(
          "auth_failed",
          "forbidden",
          "not_found",
          "rate_limited",
          "dependency_unavailable",
          "provider_timeout",
          "provider_error",
          "provider_busy",
          "provider_interrupted",
          "validation_error",
          "request_timeout",
          "payload_too_large",
          "internal_error",
          "other");
  private final MeterRegistry meters;
  private final String environment;

  public PlatformMetrics(MeterRegistry meters, ObservabilitySettings settings) {
    this.meters = meters;
    environment = settings.environment();
    meters.counter("llm_gateway_rate_limit_rejections", "environment", environment);
    meters.counter("llm_gateway_api_key_auth_failures", "environment", environment);
  }

  public static String error(int status) {
    return switch (status) {
      case 400, 422 -> "validation_error";
      case 401 -> "auth_failed";
      case 403 -> "forbidden";
      case 404 -> "not_found";
      case 408 -> "request_timeout";
      case 413, 414 -> "payload_too_large";
      case 429 -> "rate_limited";
      case 502 -> "provider_error";
      case 503 -> "dependency_unavailable";
      case 504 -> "provider_timeout";
      default -> status >= 500 ? "internal_error" : "other";
    };
  }

  public void http(
      String route, String method, int status, long nanos, Map<String, String> fields) {
    var tags = Tags.of("route", route, "method", method, "status_code", Integer.toString(status));
    meters.counter("http_requests", tags).increment();
    histogram("http_request_duration", tags, nanos);
    if (!route.equals("gateway")) return;
    String provider = "mock".equals(fields.get("provider")) ? "mock" : "unknown";
    String model = "mock-llm-small".equals(fields.get("model")) ? "mock-llm-small" : "unknown";
    var gateway = Tags.of("provider", provider, "model", model);
    meters
        .counter(
            "llm_gateway_requests", gateway.and("status", status < 400 ? "succeeded" : "failed"))
        .increment();
    histogram("llm_gateway_request_duration", gateway, nanos);
    if (status >= 400) {
      String category = fields.getOrDefault("error_category", error(status));
      meters
          .counter(
              "llm_gateway_errors",
              gateway.and("error_category", ERRORS.contains(category) ? category : "other"))
          .increment();
    }
    if (status == 401)
      meters.counter("llm_gateway_api_key_auth_failures", "environment", environment).increment();
    if (status == 429)
      meters.counter("llm_gateway_rate_limit_rejections", "environment", environment).increment();
  }

  public void routed() {
    meters
        .counter("llm_gateway_model_routing", "provider", "mock", "model", "mock-llm-small")
        .increment();
  }

  public void accepted(BigDecimal cost, int input, int output) {
    meters
        .counter("llm_gateway_estimated_cost_usd", "provider", "mock", "model", "mock-llm-small")
        .increment(cost.doubleValue());
    meters
        .counter(
            "llm_gateway_tokens",
            "provider",
            "mock",
            "model",
            "mock-llm-small",
            "token_type",
            "input")
        .increment(input);
    meters
        .counter(
            "llm_gateway_tokens",
            "provider",
            "mock",
            "model",
            "mock-llm-small",
            "token_type",
            "output")
        .increment(output);
  }

  private void histogram(String name, Tags tags, long nanos) {
    Timer.builder(name)
        .tags(tags)
        .serviceLevelObjectives(
            java.time.Duration.ofMillis(10),
            java.time.Duration.ofMillis(50),
            java.time.Duration.ofMillis(100),
            java.time.Duration.ofMillis(250),
            java.time.Duration.ofMillis(500),
            java.time.Duration.ofSeconds(1),
            java.time.Duration.ofSeconds(2),
            java.time.Duration.ofSeconds(5),
            java.time.Duration.ofSeconds(10),
            java.time.Duration.ofSeconds(30))
        .register(meters)
        .record(nanos, TimeUnit.NANOSECONDS);
  }
}
