package dev.christiankfoury.aiplatform.security;

import java.net.URI;
import java.util.Set;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("operator.security")
public record OperatorSecuritySettings(
    String mode, String issuer, String audience, String jwksUri, String environment) {
  public OperatorSecuritySettings {
    if (!Set.of("disabled", "oidc").contains(mode))
      throw new IllegalArgumentException("Unsupported operator security mode");
    if (mode.equals("oidc")) {
      endpoint(issuer, environment);
      endpoint(jwksUri, environment);
      if (audience == null || audience.isBlank() || audience.length() > 512)
        throw new IllegalArgumentException("A bounded operator audience is required");
    }
  }

  public boolean enabled() {
    return mode.equals("oidc");
  }

  private static void endpoint(String value, String environment) {
    try {
      URI uri = URI.create(value);
      boolean localHttp =
          Set.of("local", "test").contains(environment)
              && uri.getScheme().equals("http")
              && Set.of("localhost", "127.0.0.1", "[::1]").contains(uri.getHost());
      if (value.length() > 512
          || !uri.toASCIIString().equals(value)
          || uri.getHost() == null
          || uri.getUserInfo() != null
          || uri.getFragment() != null
          || uri.getQuery() != null
          || !(uri.getScheme().equals("https") || localHttp)) throw new IllegalArgumentException();
    } catch (IllegalArgumentException | NullPointerException failure) {
      throw new IllegalArgumentException(
          "Operator issuer and JWKS must be explicit HTTPS endpoints (loopback HTTP only in local tests)");
    }
  }
}
