package dev.christiankfoury.aiplatform.http;

public final class ValidationFailure extends RuntimeException {
  private static final long serialVersionUID = 1L;
  private final String field;

  public ValidationFailure(String field) {
    super("Invalid telemetry event");
    this.field = field;
  }

  public String field() {
    return field;
  }
}
