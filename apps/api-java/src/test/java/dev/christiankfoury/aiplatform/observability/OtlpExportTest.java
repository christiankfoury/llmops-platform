package dev.christiankfoury.aiplatform.observability;

import static org.assertj.core.api.Assertions.*;

import com.sun.net.httpserver.HttpServer;
import io.opentelemetry.context.Context;
import io.opentelemetry.sdk.trace.export.SpanExporter;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.support.StaticListableBeanFactory;

class OtlpExportTest {
  @Test
  void explicitOtlpHttpExportContainsSafeStagesAndCollectorFailureDoesNotFailWork()
      throws Exception {
    var receiver = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    var bodies = new ArrayBlockingQueue<byte[]>(4);
    var fail = new java.util.concurrent.atomic.AtomicBoolean();
    receiver.createContext(
        "/v1/traces",
        exchange -> {
          byte[] body = exchange.getRequestBody().readNBytes(262145);
          if (body.length <= 262144) bodies.offer(body);
          exchange.sendResponseHeaders(fail.get() ? 503 : 200, -1);
          exchange.close();
        });
    receiver.start();
    var configuration = new ObservabilityConfiguration();
    try (var sdk =
        configuration.platformOpenTelemetry(
            new ObservabilitySettings(
                "http://127.0.0.1:" + receiver.getAddress().getPort() + "/v1/traces", 1, "local"),
            new StaticListableBeanFactory().getBeanProvider(SpanExporter.class))) {
      var tracer = new OperationsTracer(sdk);
      var server = tracer.server("gateway", "POST", null);
      var scope = server.makeCurrent();
      try (var worker = Executors.newSingleThreadExecutor()) {
        var result =
            worker
                .submit(
                    Context.current()
                        .wrap(
                            (Callable<Integer>)
                                () -> tracer.stage("gateway.provider.call", () -> 42)))
                .get(2, TimeUnit.SECONDS);
        assertThat(result).isEqualTo(42);
        assertThat(
                worker
                    .submit(
                        () -> io.opentelemetry.api.trace.Span.current().getSpanContext().isValid())
                    .get())
            .isFalse();
      } finally {
        scope.close();
        server.end();
      }
      sdk.getSdkTracerProvider().forceFlush().join(3, TimeUnit.SECONDS);
      byte[] exported = bodies.poll(3, TimeUnit.SECONDS);
      assertThat(exported).isNotNull();
      assertThat(new String(exported, StandardCharsets.ISO_8859_1))
          .contains("gateway.provider.call", "http.gateway", "ai-platform-api");
      fail.set(true);
      long started = System.nanoTime();
      assertThat(tracer.stage("gateway.provider.call", () -> "still-serving"))
          .isEqualTo("still-serving");
      assertThat(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started)).isLessThan(500);
      sdk.getSdkTracerProvider().forceFlush().join(3, TimeUnit.SECONDS);
      assertThat(bodies.poll(3, TimeUnit.SECONDS)).isNotNull();
    } finally {
      receiver.stop(0);
    }
  }
}
