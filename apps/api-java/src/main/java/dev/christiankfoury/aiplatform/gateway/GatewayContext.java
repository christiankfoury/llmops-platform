package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator.Scope;
import java.util.UUID;

public record GatewayContext(
    Scope scope,
    UUID promptId,
    int promptVersion,
    String promptContent,
    UUID routeId,
    String provider,
    String model) {
  @Override
  public String toString() {
    return "GatewayContext[routeId=" + routeId + "]";
  }
}
