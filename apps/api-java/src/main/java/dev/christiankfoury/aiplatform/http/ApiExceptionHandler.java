package dev.christiankfoury.aiplatform.http;

import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

@RestControllerAdvice
public class ApiExceptionHandler extends ResponseEntityExceptionHandler {
  private static final Logger LOG = LoggerFactory.getLogger(ApiExceptionHandler.class);

  @Override
  protected ResponseEntity<Object> handleMethodArgumentNotValid(
      MethodArgumentNotValidException exception,
      HttpHeaders headers,
      HttpStatusCode status,
      WebRequest request) {
    List<Map<String, Object>> errors =
        exception.getBindingResult().getFieldErrors().stream()
            .map(
                error ->
                    Map.<String, Object>of(
                        "loc",
                        List.of(
                            "body",
                            error
                                .getField()
                                .replaceAll("([a-z0-9])([A-Z])", "$1_$2")
                                .toLowerCase(java.util.Locale.ROOT)),
                        "msg",
                        "Invalid value",
                        "type",
                        "validation_error"))
            .toList();
    return ResponseEntity.status(422).headers(headers).body(Map.of("detail", errors));
  }

  @Override
  protected ResponseEntity<Object> handleExceptionInternal(
      Exception exception,
      Object body,
      HttpHeaders headers,
      HttpStatusCode status,
      WebRequest request) {
    HttpStatus known = HttpStatus.resolve(status.value());
    String detail = known == null ? "Request failed" : known.getReasonPhrase();
    // Never forward framework bodies: they can contain rejected values, URIs or exception text.
    return ResponseEntity.status(status).headers(headers).body(Map.of("detail", detail));
  }

  @ExceptionHandler(ApiFailure.class)
  public ResponseEntity<Map<String, String>> applicationFailure(ApiFailure failure) {
    return ResponseEntity.status(failure.status()).body(Map.of("detail", failure.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<Map<String, String>> unexpected(Exception exception) {
    LOG.error("api_failure type={}", exception.getClass().getSimpleName());
    return ResponseEntity.internalServerError().body(Map.of("detail", "Internal server error"));
  }
}
