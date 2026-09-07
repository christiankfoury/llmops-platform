package dev.christiankfoury.aiplatform.operator;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/** Temporary local-only boundary until the OIDC/project-authorization phase. */
@Component
public class LocalOperatorAccess implements HandlerInterceptor, WebMvcConfigurer {
  private static final Set<String> LOOPBACK = Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1");
  private static final Pattern HOST =
      Pattern.compile("(?:localhost|127\\.0\\.0\\.1|\\[::1\\])(?::[0-9]{1,5})?");
  private final boolean local;
  private final String[] origins;

  public LocalOperatorAccess(
      @Value("${server.address}") String bind,
      @Value("${platform.environment}") String environment,
      @Value("${server.port}") int port) {
    local = (LOOPBACK.contains(bind) || bind.equals("localhost")) && environment.equals("local");
    origins =
        new String[] {
          "http://localhost:3000",
          "http://127.0.0.1:3000",
          "http://localhost:" + port,
          "http://127.0.0.1:" + port,
          "http://[::1]:" + port
        };
  }

  @Override
  public boolean preHandle(
      HttpServletRequest request, HttpServletResponse response, Object handler) {
    String host = request.getHeader("Host");
    if (host == null) host = request.getServerName();
    String origin = request.getHeader("Origin");
    if (!local
        || !LOOPBACK.contains(request.getRemoteAddr())
        || !HOST.matcher(host.toLowerCase(Locale.ROOT)).matches()
        || (origin != null && !java.util.Arrays.asList(origins).contains(origin)))
      throw new ApiFailure(403, "Operator APIs require isolated local access");
    return true;
  }

  @Override
  public void addInterceptors(InterceptorRegistry registry) {
    registry
        .addInterceptor(this)
        .addPathPatterns("/v1/usage/**", "/v1/admin/**")
        .excludePathPatterns("/v1/usage/llm-events");
  }

  @Override
  public void addCorsMappings(CorsRegistry registry) {
    for (String path : new String[] {"/v1/usage/**", "/v1/admin/**"})
      registry
          .addMapping(path)
          .allowedOrigins(origins)
          .allowedMethods("GET", "HEAD", "POST", "PATCH", "OPTIONS")
          .allowedHeaders("Content-Type")
          .allowCredentials(false)
          .maxAge(600);
  }
}
