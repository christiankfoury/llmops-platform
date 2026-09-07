package dev.christiankfoury.aiplatform.gateway;

import java.math.BigDecimal;
import java.math.RoundingMode;

public final class MockPricing {
  private MockPricing() {}

  public static BigDecimal cost(int inputTokens, int outputTokens) {
    if (inputTokens < 0 || outputTokens < 0) throw new ProviderFailure(ProviderFailure.Kind.ERROR);
    return BigDecimal.valueOf(inputTokens)
        .multiply(new BigDecimal("0.0000001"))
        .add(BigDecimal.valueOf(outputTokens).multiply(new BigDecimal("0.0000002")))
        .setScale(6, RoundingMode.HALF_UP);
  }
}
