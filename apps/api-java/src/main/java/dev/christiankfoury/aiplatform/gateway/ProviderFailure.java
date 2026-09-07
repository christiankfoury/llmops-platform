package dev.christiankfoury.aiplatform.gateway;

public final class ProviderFailure extends RuntimeException {
  private static final long serialVersionUID = 1L;

  public enum Kind {
    ERROR(502, "Provider failure", "provider_error", true),
    TIMEOUT(504, "Provider timeout", "provider_timeout", true),
    BUSY(503, "Provider capacity unavailable", "provider_busy", false),
    INTERRUPTED(503, "Provider call interrupted", "provider_interrupted", false);
    private final int status;
    private final String detail;
    private final String category;
    private final boolean retryable;

    Kind(int status, String detail, String category, boolean retryable) {
      this.status = status;
      this.detail = detail;
      this.category = category;
      this.retryable = retryable;
    }

    public int status() {
      return status;
    }

    public String detail() {
      return detail;
    }

    public String category() {
      return category;
    }

    public boolean retryable() {
      return retryable;
    }
  }

  private final Kind kind;

  public ProviderFailure(Kind kind) {
    super(kind.detail());
    this.kind = kind;
  }

  public Kind kind() {
    return kind;
  }
}
