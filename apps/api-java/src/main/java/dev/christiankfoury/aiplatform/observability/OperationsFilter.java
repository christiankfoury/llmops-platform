package dev.christiankfoury.aiplatform.observability;

import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.StatusCode;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.Set;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 15)
public class OperationsFilter extends OncePerRequestFilter {
  private final OperationsTracer tracer;
  private final PlatformMetrics metrics;

  public OperationsFilter(OperationsTracer tracer, PlatformMetrics metrics) {
    this.tracer = tracer;
    this.metrics = metrics;
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    return !request.getRequestURI().startsWith("/v1/");
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    String path = request.getRequestURI();
    String route =
        path.equals("/v1/gateway/completions")
            ? "gateway"
            : path.equals("/v1/usage/llm-events")
                ? "telemetry"
                : path.startsWith("/v1/admin/")
                        || path.startsWith("/v1/usage/")
                        || path.startsWith("/v1/operator/")
                    ? "operator"
                    : "other";
    String method =
        Set.of("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
                .contains(request.getMethod())
            ? request.getMethod()
            : "OTHER";
    var fields = OperationalContext.open();
    var span = tracer.server(route, method, request.getHeader("traceparent"));
    var scope = span.makeCurrent();
    long started = System.nanoTime();
    boolean failed = false;
    try {
      OperationalContext.put("request_id", request.getAttribute("platform.request_id"));
      OperationalContext.put("trace_id", span.getSpanContext().getTraceId());
      OperationalContext.put("span_id", span.getSpanContext().getSpanId());
      OperationalContext.put("route", route);
      OperationalContext.put("method", method);
      response.setHeader("X-Trace-ID", span.getSpanContext().getTraceId());
      chain.doFilter(request, response);
    } catch (IOException | ServletException | RuntimeException failure) {
      failed = true;
      throw failure;
    } finally {
      int status = failed ? 500 : Math.clamp(response.getStatus(), 100, 599);
      long nanos = Math.max(0, System.nanoTime() - started);
      OperationalContext.put("status_code", status);
      OperationalContext.put("latency_ms", nanos / 1000000);
      if (status >= 400) fields.putIfAbsent("error_category", PlatformMetrics.error(status));
      span.setAttribute("http.response.status_code", status);
      if (status >= 500) span.setStatus(StatusCode.ERROR);
      Object writing = request.getAttribute("platform.response_span");
      if (writing instanceof Span writeSpan) {
        if (status >= 500) writeSpan.setStatus(StatusCode.ERROR);
        writeSpan.end();
      }
      try {
        metrics.http(route, method, status, nanos, fields);
        var log = LoggerFactory.getLogger("platform.operations");
        var event = status >= 500 ? log.atError() : status >= 400 ? log.atWarn() : log.atInfo();
        fields.forEach(event::addKeyValue);
        event.log("request_completed");
      } finally {
        scope.close();
        span.end();
        OperationalContext.close();
      }
    }
  }
}
