package dev.christiankfoury.aiplatform.gateway;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("gateway.provider")
public record ProviderSettings(
    int maxAttempts, Duration timeout, Duration retryBackoff, int concurrency) {
  public ProviderSettings {
    if (maxAttempts < 1
        || maxAttempts > 3
        || timeout == null
        || timeout.toMillis() < 10
        || timeout.toMillis() > 60000
        || retryBackoff == null
        || retryBackoff.isNegative()
        || retryBackoff.toMillis() > 1000
        || concurrency < 1
        || concurrency > 32) {
      throw new IllegalArgumentException("Provider execution settings exceed supported bounds");
    }
  }
}
