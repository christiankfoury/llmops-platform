package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class GatewayService {
  private final GatewayConfiguration configuration;
  private final ProviderCaller provider;
  private final GatewayRecorder recorder;
  private final dev.christiankfoury.aiplatform.reliability.RedisAdmission admission;

  public GatewayService(
      GatewayConfiguration configuration,
      ProviderCaller provider,
      GatewayRecorder recorder,
      dev.christiankfoury.aiplatform.reliability.RedisAdmission admission) {
    this.configuration = configuration;
    this.provider = provider;
    this.recorder = recorder;
    this.admission = admission;
  }

  public CompletionResponse complete(String key, CompletionRequest request) {
    long started = System.nanoTime();
    GatewayContext context = configuration.resolve(key, request);
    admission.key(
        dev.christiankfoury.aiplatform.reliability.RedisAdmission.Traffic.GATEWAY,
        context.scope().keyId());
    String requestId = "req_" + UUID.randomUUID().toString().replace("-", "");
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
      recorder.failure(context, requestId, elapsed(started), failure.kind().category());
      throw new ApiFailure(failure.kind().status(), failure.kind().detail());
    }
    int latency = elapsed(started);
    var cost = MockPricing.cost(result.inputTokens(), result.outputTokens());
    recorder.success(context, requestId, latency, result, cost);
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
