package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.persistence.model.GatewayRequest;
import java.util.UUID;

public record TelemetryResponse(
    boolean accepted,
    boolean duplicate,
    String requestId,
    String externalEventId,
    String externalRequestId,
    UUID projectId,
    UUID applicationId,
    String status) {
  public static TelemetryResponse from(GatewayRequest request, boolean duplicate) {
    return new TelemetryResponse(
        true,
        duplicate,
        request.getRequestId(),
        request.getExternalEventId(),
        request.getExternalRequestId(),
        request.getProjectId(),
        request.getApplicationId(),
        request.getStatus());
  }
}
