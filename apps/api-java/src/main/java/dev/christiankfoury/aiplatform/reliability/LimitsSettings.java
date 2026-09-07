package dev.christiankfoury.aiplatform.reliability;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("platform.limits")
public record LimitsSettings(
    String namespace,
    int globalLimit,
    int gatewayLimit,
    int telemetryLimit,
    Duration window,
    int concurrentRequests) {
  public LimitsSettings {
    if (namespace == null
        || !namespace.matches("[a-zA-Z0-9:_-]{1,64}")
        || globalLimit < 1
        || globalLimit > 100000
        || gatewayLimit < 1
        || gatewayLimit > 10000
        || telemetryLimit < 1
        || telemetryLimit > 10000
        || window == null
        || window.toMillis() < 100
        || window.toMillis() > 3600000
        || concurrentRequests < 1
        || concurrentRequests > 48)
      throw new IllegalArgumentException("Admission settings exceed supported bounds");
  }
}
