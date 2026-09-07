package dev.christiankfoury.aiplatform.reliability;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.util.concurrent.Semaphore;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class AdmissionFilter extends OncePerRequestFilter {
  private final RedisAdmission admission;
  private final DependencyReadiness readiness;
  private final Semaphore permits;

  public AdmissionFilter(
      RedisAdmission admission, DependencyReadiness readiness, LimitsSettings settings) {
    this.admission = admission;
    this.readiness = readiness;
    permits = new Semaphore(settings.concurrentRequests());
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    return !request.getRequestURI().startsWith("/v1/");
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    if (!readiness.ready() || !permits.tryAcquire()) {
      reject(response, 503, "Service unavailable", 1);
      return;
    }
    try {
      String path = request.getRequestURI();
      if (path.length() > 2048
          || request.getQueryString() != null && request.getQueryString().length() > 4096) {
        reject(response, 414, "URI too long", 0);
        return;
      }
      RedisAdmission.Traffic traffic =
          path.equals("/v1/gateway/completions")
              ? RedisAdmission.Traffic.GATEWAY
              : path.equals("/v1/usage/llm-events")
                  ? RedisAdmission.Traffic.TELEMETRY
                  : RedisAdmission.Traffic.OPERATOR;
      // Three fixed keys before authentication: random credentials never create Redis key state.
      admission.global(traffic);
      int maximum = traffic == RedisAdmission.Traffic.OPERATOR ? 262144 : 32768;
      if (request.getContentLengthLong() > maximum) {
        reject(response, 413, "Payload too large", 0);
        return;
      }
      if (request.getMethod().equals("POST")
          || request.getMethod().equals("PATCH")
          || request.getContentLengthLong() > 0) {
        byte[] body = readBody(request, maximum);
        if (body.length > maximum) {
          reject(response, 413, "Payload too large", 0);
          return;
        }
        request = new BoundedRequest(request, body);
      }
      chain.doFilter(request, response);
    } catch (RateLimitFailure failure) {
      reject(response, 429, "Rate limit exceeded", failure.retryAfterSeconds());
    } catch (ApiFailure failure) {
      reject(response, failure.status(), failure.getMessage(), failure.status() == 503 ? 1 : 0);
    } catch (IOException failure) {
      Throwable cause = failure;
      boolean timeout = false;
      for (int depth = 0; cause != null && depth < 6; depth++, cause = cause.getCause())
        if (cause instanceof SocketTimeoutException) timeout = true;
      if (timeout) reject(response, 408, "Request timeout", 0);
      else throw failure;
    } finally {
      permits.release();
    }
  }

  private static byte[] readBody(HttpServletRequest request, int maximum) throws IOException {
    long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(5);
    var output = new java.io.ByteArrayOutputStream(Math.min(maximum + 1, 4096));
    byte[] buffer = new byte[4096];
    var input = request.getInputStream();
    while (output.size() <= maximum) {
      if (System.nanoTime() >= deadline) throw new SocketTimeoutException();
      int read = input.read(buffer, 0, Math.min(buffer.length, maximum + 1 - output.size()));
      if (System.nanoTime() >= deadline) throw new SocketTimeoutException();
      if (read < 0) break;
      output.write(buffer, 0, read);
    }
    return output.toByteArray();
  }

  private static void reject(HttpServletResponse response, int status, String detail, long retry)
      throws IOException {
    response.setStatus(status);
    response.setContentType("application/json");
    response.setHeader("Cache-Control", "no-store");
    if (retry > 0) response.setHeader("Retry-After", Long.toString(retry));
    response.getWriter().write("{\"detail\":\"" + detail + "\"}");
  }
}
