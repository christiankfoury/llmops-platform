package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.http.ValidationFailure;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class TelemetryController {
  private final ApplicationAuthenticator authenticator;
  private final TelemetryNormalizer normalizer;
  private final TelemetryAttribution attribution;
  private final TelemetryWriter writer;
  private final TelemetryMetrics metrics;

  public TelemetryController(
      ApplicationAuthenticator authenticator,
      TelemetryNormalizer normalizer,
      TelemetryAttribution attribution,
      TelemetryWriter writer,
      TelemetryMetrics metrics) {
    this.authenticator = authenticator;
    this.normalizer = normalizer;
    this.attribution = attribution;
    this.writer = writer;
    this.metrics = metrics;
  }

  @PostMapping(value = "/v1/usage/llm-events", consumes = "application/json")
  @ResponseStatus(HttpStatus.ACCEPTED)
  public TelemetryResponse ingest(
      @RequestHeader(value = "X-API-Key", required = false) String key, HttpServletRequest request)
      throws IOException {
    TelemetryEvent event = null;
    try {
      var scope = authenticator.authenticate(key);
      // Read at most one byte beyond the bound, including requests without Content-Length.
      event =
          normalizer.normalize(
              request.getInputStream().readNBytes(TelemetryJson.MAX_BODY_BYTES + 1));
      attribution.verify(scope, event);
      var response = writer.write(scope, event);
      // The transaction has committed before cost/token counters are incremented.
      metrics.outcome(
          event,
          response.duplicate() ? "duplicate" : "accepted",
          response.duplicate() ? null : event.text("error_category"));
      return response;
    } catch (ValidationFailure failure) {
      metrics.outcome(event, "rejected", "validation_error");
      throw failure;
    } catch (ApiFailure failure) {
      String category =
          switch (failure.status()) {
            case 401 -> "auth_failed";
            case 403 -> "attribution_failed";
            case 409 -> "duplicate_conflict";
            case 413 -> "payload_too_large";
            default -> "other";
          };
      metrics.outcome(event, "rejected", category);
      throw failure;
    } catch (RuntimeException failure) {
      metrics.outcome(event, "rejected", "storage_failed");
      throw failure;
    }
  }
}
