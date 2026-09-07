package dev.christiankfoury.aiplatform.http;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class RequestIdFilter extends OncePerRequestFilter {
  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    String id = request.getHeader("X-Request-ID");
    if (id == null || !id.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}")) {
      id = "http_" + UUID.randomUUID().toString().replace("-", "");
    }
    request.setAttribute("platform.request_id", id);
    response.setHeader("X-Request-ID", id);
    chain.doFilter(request, response);
  }
}
