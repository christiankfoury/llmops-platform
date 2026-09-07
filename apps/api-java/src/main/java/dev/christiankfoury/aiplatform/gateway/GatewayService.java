package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.observability.*;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class GatewayService {
  private final OperationsTracer tracing;
  private final PlatformMetrics metrics;
  private final GatewayConfiguration configuration;
  private final ProviderCaller provider;
  private final GatewayRecorder recorder;
  private final dev.christiankfoury.aiplatform.reliability.RedisAdmission admission;

  public GatewayService(
      OperationsTracer tracing,
      PlatformMetrics metrics,
      GatewayConfiguration configuration,
      ProviderCaller provider,
      GatewayRecorder recorder,
      dev.christiankfoury.aiplatform.reliability.RedisAdmission admission) {
    this.tracing = tracing;
    this.metrics = metrics;
    this.configuration = configuration;
    this.provider = provider;
    this.recorder = recorder;
    this.admission = admission;
  }

  public CompletionResponse complete(String key, CompletionRequest request) {
    long started = System.nanoTime();
    GatewayContext context = configuration.resolve(key, request);
    OperationalContext.put("project_id", context.scope().projectId());
    OperationalContext.put("application_id", context.scope().applicationId());
    OperationalContext.put("prompt_version", context.promptVersion());
    OperationalContext.put("provider", context.provider());
    OperationalContext.put("model", context.model());
    metrics.routed();
    admission.key(
        dev.christiankfoury.aiplatform.reliability.RedisAdmission.Traffic.GATEWAY,
        context.scope().keyId());
    String requestId = "req_" + UUID.randomUUID().toString().replace("-", "");
    OperationalContext.put("gateway_request_id", requestId);
    CompletionProvider.Result result;
    try {
      result = provider.complete(context, request.getInput());
      if (result == null
          || result.output() == null
          || result.inputTokens() < 0
          || result.outputTokens() < 0
          || result.output().length() > 100000
          || result.inputTokens() > 1000000
          || result.outputTokens() > 1000000) {
        throw new ProviderFailure(ProviderFailure.Kind.ERROR);
      }
    } catch (ProviderFailure failure) {
      OperationalContext.put("error_category", failure.kind().category());
      tracing.stage(
          "gateway.database.write",
          () -> {
            recorder.failure(context, requestId, elapsed(started), failure.kind().category());
            return null;
          });
      throw new ApiFailure(failure.kind().status(), failure.kind().detail());
    }
    int latency = elapsed(started);
    var cost = MockPricing.cost(result.inputTokens(), result.outputTokens());
    tracing.stage(
        "gateway.database.write",
        () -> {
          recorder.success(context, requestId, latency, result, cost);
          return null;
        });
    // The transactional recorder returned only after committing its request and cost row.
    metrics.accepted(cost, result.inputTokens(), result.outputTokens());
    OperationalContext.put("estimated_cost_usd", cost.toPlainString());
    OperationalContext.put("input_tokens", result.inputTokens());
    OperationalContext.put("output_tokens", result.outputTokens());
    return new CompletionResponse(
        requestId,
        "succeeded",
        context.provider(),
        context.model(),
        result.output(),
        context.promptVersion(),
        latency,
        result.inputTokens(),
        result.outputTokens(),
        cost);
  }

  private static int elapsed(long started) {
    return (int) Math.min(Integer.MAX_VALUE, Math.max(1, (System.nanoTime() - started) / 1000000));
  }
}
