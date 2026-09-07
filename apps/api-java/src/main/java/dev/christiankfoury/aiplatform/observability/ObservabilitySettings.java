package dev.christiankfoury.aiplatform.observability;

import java.net.URI;
import java.util.Set;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("platform.observability")
public record ObservabilitySettings(String endpoint, double sampleProbability, String environment) {
  public ObservabilitySettings {
    if (!Double.isFinite(sampleProbability) || sampleProbability < 0 || sampleProbability > 1)
      throw new IllegalArgumentException("Trace sample probability must be between zero and one");
    if (endpoint == null) endpoint = "";
    if (!endpoint.isBlank()) {
      URI uri = URI.create(endpoint);
      boolean local = Set.of("local", "test").contains(environment);
      if (uri.getHost() == null
          || uri.getUserInfo() != null
          || uri.getQuery() != null
          || uri.getFragment() != null
          || endpoint.length() > 512
          || !("https".equals(uri.getScheme()) || local && "http".equals(uri.getScheme())))
        throw new IllegalArgumentException(
            "OTLP requires an explicit safe endpoint and hosted HTTPS");
    }
    if (!Set.of("local", "test", "dev", "staging", "prod").contains(environment))
      environment = "other";
  }

  @Override
  public String toString() {
    return "ObservabilitySettings[endpoint omitted]";
  }
}
