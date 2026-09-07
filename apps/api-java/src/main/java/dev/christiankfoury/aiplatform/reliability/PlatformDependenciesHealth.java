package dev.christiankfoury.aiplatform.reliability;

import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

@Component("platformDependencies")
public class PlatformDependenciesHealth implements HealthIndicator {
  private final DependencyReadiness readiness;

  public PlatformDependenciesHealth(DependencyReadiness readiness) {
    this.readiness = readiness;
  }

  @Override
  public Health health() {
    return (readiness.ready() ? Health.up() : Health.down()).build();
  }
}
