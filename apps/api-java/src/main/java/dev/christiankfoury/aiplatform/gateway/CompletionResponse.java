package dev.christiankfoury.aiplatform.gateway;

import java.math.BigDecimal;

public record CompletionResponse(
    String requestId,
    String status,
    String provider,
    String model,
    String output,
    int promptVersion,
    int latencyMs,
    int inputTokens,
    int outputTokens,
    BigDecimal estimatedCostUsd) {
  @Override
  public String toString() {
    return "CompletionResponse[requestId=" + requestId + ", status=" + status + "]";
  }
}
