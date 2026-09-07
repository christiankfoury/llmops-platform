package dev.christiankfoury.aiplatform.gateway;

public interface CompletionProvider {
  record Result(String output, int inputTokens, int outputTokens) {
    @Override
    public String toString() {
      return "ProviderResult[content omitted]";
    }
  }

  Result complete(GatewayContext context, String input, int attempt);
}
