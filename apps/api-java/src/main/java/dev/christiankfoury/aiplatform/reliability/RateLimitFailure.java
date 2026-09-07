package dev.christiankfoury.aiplatform.reliability;

public final class RateLimitFailure extends RuntimeException {
  private static final long serialVersionUID = 1L;
  private final long retryAfterSeconds;

  public RateLimitFailure(long milliseconds) {
    super("Rate limit exceeded");
    retryAfterSeconds = Math.max(1, (milliseconds + 999) / 1000);
  }

  public long retryAfterSeconds() {
    return retryAfterSeconds;
  }
}
