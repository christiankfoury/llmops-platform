package dev.christiankfoury.aiplatform.observability;

import dev.christiankfoury.aiplatform.reliability.DependencyReadiness;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.MeterBinder;
import org.springframework.stereotype.Component;

@Component
public class DependencyMetrics implements MeterBinder {
  private final DependencyReadiness readiness;

  public DependencyMetrics(DependencyReadiness readiness) {
    this.readiness = readiness;
  }

  @Override
  public void bindTo(MeterRegistry registry) {
    Gauge.builder("platform_dependency_up", readiness, value -> value.databaseHealthy() ? 1 : 0)
        .tag("dependency", "postgresql")
        .register(registry);
    Gauge.builder("platform_dependency_up", readiness, value -> value.redisHealthy() ? 1 : 0)
        .tag("dependency", "redis")
        .register(registry);
    Gauge.builder("platform_ready", readiness, value -> value.ready() ? 1 : 0).register(registry);
  }
}
