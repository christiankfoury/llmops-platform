package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.persistence.model.CostRecord;
import dev.christiankfoury.aiplatform.persistence.model.GatewayRequest;
import dev.christiankfoury.aiplatform.persistence.repository.CostRecordRepository;
import dev.christiankfoury.aiplatform.persistence.repository.GatewayRequestRepository;
import java.math.BigDecimal;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GatewayRecorder {
  private final GatewayRequestRepository requests;
  private final CostRecordRepository costs;

  public GatewayRecorder(GatewayRequestRepository requests, CostRecordRepository costs) {
    this.requests = requests;
    this.costs = costs;
  }

  @Transactional
  public void success(
      GatewayContext context,
      String requestId,
      int latency,
      CompletionProvider.Result result,
      BigDecimal cost) {
    GatewayRequest request = base(context, requestId, latency);
    request.setStatus("succeeded");
    request.setEstimatedInputTokens(result.inputTokens());
    request.setEstimatedOutputTokens(result.outputTokens());
    request.setEstimatedCostUsd(cost);
    requests.saveAndFlush(request);
    CostRecord record = new CostRecord();
    record.setGatewayRequestId(request.getId());
    record.setProjectId(context.scope().projectId());
    record.setApplicationId(context.scope().applicationId());
    record.setProvider(context.provider());
    record.setModelName(context.model());
    record.setInputTokens(result.inputTokens());
    record.setOutputTokens(result.outputTokens());
    record.setEstimatedCostUsd(cost);
    costs.saveAndFlush(record);
  }

  @Transactional
  public void failure(GatewayContext context, String requestId, int latency, String category) {
    GatewayRequest request = base(context, requestId, latency);
    request.setStatus("failed");
    request.setErrorCategory(category);
    requests.saveAndFlush(request);
  }

  private GatewayRequest base(GatewayContext context, String requestId, int latency) {
    GatewayRequest request = new GatewayRequest();
    request.setRequestId(requestId);
    request.setProjectId(context.scope().projectId());
    request.setApplicationId(context.scope().applicationId());
    request.setApiKeyId(context.scope().keyId());
    request.setPromptVersionId(context.promptId());
    request.setModelRouteId(context.routeId());
    request.setProvider(context.provider());
    request.setModelName(context.model());
    request.setLatencyMs(latency);
    return request;
  }
}
