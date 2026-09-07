package dev.christiankfoury.aiplatform.observability;

import io.micrometer.core.instrument.config.MeterFilter;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.exporter.otlp.http.trace.OtlpHttpSpanExporter;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.SpanLimits;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.sdk.trace.export.SpanExporter;
import io.opentelemetry.sdk.trace.samplers.Sampler;
import java.time.Duration;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(ObservabilitySettings.class)
public class ObservabilityConfiguration {
  @Bean(destroyMethod = "close")
  OpenTelemetrySdk platformOpenTelemetry(
      ObservabilitySettings settings, ObjectProvider<SpanExporter> testExporters) {
    var provider =
        SdkTracerProvider.builder()
            .setResource(
                Resource.create(
                    Attributes.builder()
                        .put("service.name", "ai-platform-api")
                        .put("deployment.environment.name", settings.environment())
                        .build()))
            // Do not let a remote sampled flag force every request to be exported.
            .setSampler(Sampler.traceIdRatioBased(settings.sampleProbability()))
            .setSpanLimits(
                SpanLimits.builder()
                    .setMaxNumberOfAttributes(16)
                    .setMaxAttributeValueLength(128)
                    .setMaxNumberOfEvents(0)
                    .setMaxNumberOfLinks(0)
                    .build());
    SpanExporter exporter = testExporters.getIfAvailable();
    if (exporter == null && !settings.endpoint().isBlank()) {
      exporter =
          OtlpHttpSpanExporter.builder()
              .setEndpoint(settings.endpoint())
              .setConnectTimeout(Duration.ofSeconds(1))
              .setTimeout(Duration.ofSeconds(1))
              .build();
    }
    if (exporter != null)
      provider.addSpanProcessor(
          BatchSpanProcessor.builder(exporter)
              .setMaxQueueSize(512)
              .setMaxExportBatchSize(64)
              .setScheduleDelay(Duration.ofSeconds(1))
              .setExporterTimeout(Duration.ofSeconds(1))
              .build());
    return OpenTelemetrySdk.builder().setTracerProvider(provider.build()).build();
  }

  @Bean
  MeterFilter boundedHttpInstrumentation() {
    // The explicit HTTP meters cover pre-auth refusals using a fixed route/method vocabulary.
    return MeterFilter.denyNameStartsWith("http.server.requests");
  }
}
