package dev.christiankfoury.aiplatform.observability;

import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.*;
import io.opentelemetry.context.Context;
import java.util.Set;
import java.util.function.Supplier;
import org.springframework.stereotype.Component;

@Component
public class OperationsTracer {
  private final Tracer tracer;
  private static final Set<String> STAGES =
      Set.of(
          "gateway.authentication",
          "gateway.prompt.lookup",
          "gateway.model.routing",
          "gateway.provider.call",
          "gateway.database.write",
          "http.response.write",
          "telemetry.validation",
          "telemetry.database.write");

  public OperationsTracer(OpenTelemetry sdk) {
    tracer = sdk.getTracer("ai-platform.operations", "1");
  }

  public Span stageSpan(String name) {
    if (!STAGES.contains(name)) throw new IllegalArgumentException("Unknown operational stage");
    return tracer.spanBuilder(name).startSpan();
  }

  public <T> T stage(String name, Supplier<T> action) {
    var span = stageSpan(name);
    var scope = span.makeCurrent();
    try {
      return action.get();
    } catch (RuntimeException failure) {
      span.setStatus(StatusCode.ERROR);
      throw failure;
    } finally {
      scope.close();
      span.end();
    }
  }

  public Span server(String route, String method, String parent) {
    Context context = Context.root();
    // Accept only W3C version 00; never read baggage, tracestate, URLs, queries or other headers.
    if (parent != null && parent.matches("00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}")) {
      var incoming =
          SpanContext.createFromRemoteParent(
              parent.substring(3, 35),
              parent.substring(36, 52),
              TraceFlags.fromHex(parent, 53),
              TraceState.getDefault());
      if (incoming.isValid()) context = context.with(Span.wrap(incoming));
    }
    return tracer
        .spanBuilder("http." + route)
        .setParent(context)
        .setSpanKind(SpanKind.SERVER)
        .setAttribute("http.route", route)
        .setAttribute("http.request.method", method)
        .startSpan();
  }
}
