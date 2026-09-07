package dev.christiankfoury.aiplatform.observability;

import org.springframework.core.MethodParameter;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.*;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;

@RestControllerAdvice
public class ResponseTracingAdvice implements ResponseBodyAdvice<Object> {
  private final OperationsTracer tracer;

  public ResponseTracingAdvice(OperationsTracer tracer) {
    this.tracer = tracer;
  }

  @Override
  public boolean supports(
      MethodParameter method, Class<? extends HttpMessageConverter<?>> converter) {
    return true;
  }

  @Override
  public Object beforeBodyWrite(
      Object body,
      MethodParameter method,
      MediaType type,
      Class<? extends HttpMessageConverter<?>> converter,
      ServerHttpRequest request,
      ServerHttpResponse response) {
    if (request instanceof ServletServerHttpRequest servlet) {
      var nativeRequest = servlet.getServletRequest();
      if (nativeRequest.getRequestURI().startsWith("/v1/")
          && nativeRequest.getAttribute("platform.response_span") == null)
        nativeRequest.setAttribute(
            "platform.response_span", tracer.stageSpan("http.response.write"));
    }
    return body;
  }
}
