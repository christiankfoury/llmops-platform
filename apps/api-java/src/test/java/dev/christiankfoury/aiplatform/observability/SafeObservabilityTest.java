package dev.christiankfoury.aiplatform.observability;

import static org.assertj.core.api.Assertions.*;

import ch.qos.logback.classic.*;
import ch.qos.logback.classic.spi.*;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.slf4j.event.KeyValuePair;
import org.springframework.mock.env.MockEnvironment;

class SafeObservabilityTest {
  @Test
  void formatterDropsRawErrorsArgumentsMdcAndUnapprovedFields() {
    var context = new LoggerContext();
    try {
      var event =
          new LoggingEvent(
              "example",
              context.getLogger("platform.operations"),
              Level.ERROR,
              "request_completed",
              new IllegalStateException("secret-exception-sentinel"),
              new Object[] {"secret-argument-sentinel"});
      event.setMDCPropertyMap(
          Map.of("authorization", "secret-token-sentinel", "traceId", "secret-mdc-sentinel"));
      event.addKeyValuePair(new KeyValuePair("request_id", "safe-request-id"));
      event.addKeyValuePair(new KeyValuePair("input", "secret-input-sentinel"));
      event.addKeyValuePair(new KeyValuePair("model", "secret-model-sentinel"));
      event.addKeyValuePair(new KeyValuePair("error_category", "secret-diagnostic-sentinel"));
      event.addKeyValuePair(new KeyValuePair("status_code", "500"));
      event.addKeyValuePair(new KeyValuePair("estimated_cost_usd", "0.000005"));
      event.addKeyValuePair(new KeyValuePair("trace_id", "00000000000000000000000000000001"));
      String json = new SafeLogFormatter().format(event);
      assertThat(json)
          .contains("safe-request-id", "0.000005", "\"status_code\":\"500\"")
          .doesNotContain("secret-", "stack", "authorization");
      var database =
          new LoggingEvent(
              "example",
              context.getLogger("org.hibernate.orm.jdbc.error"),
              Level.ERROR,
              "secret-sql-statement-sentinel {}",
              new IllegalStateException("secret-db-value-sentinel"),
              new Object[] {"secret-binding-sentinel"});
      assertThat(new SafeLogFormatter().format(database))
          .contains("framework_event", "org.hibernate.orm.jdbc.error")
          .doesNotContain("secret-");
    } finally {
      context.stop();
    }
  }

  @Test
  void settingsRequireSeparateManagementAndSafeExplicitExport() {
    assertThatThrownBy(
            () ->
                new ManagementListenerGuard(
                    new MockEnvironment()
                        .withProperty("server.port", "8080")
                        .withProperty("management.server.port", "8080")))
        .isInstanceOf(IllegalArgumentException.class);
    new ManagementListenerGuard(
        new MockEnvironment()
            .withProperty("server.port", "8080")
            .withProperty("management.server.port", "9080"));
    assertThatThrownBy(
            () ->
                new ObservabilitySettings("http://collector.example.invalid/v1/traces", 1, "prod"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () ->
                new ObservabilitySettings(
                    "https://user:secret@collector.example.invalid/v1/traces", 1, "prod"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ObservabilitySettings("", Double.NaN, "local"))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
