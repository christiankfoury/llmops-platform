package dev.christiankfoury.aiplatform.operator;

public class OperatorValidationFailure extends RuntimeException {
  private static final long serialVersionUID = 1L;
  private final String field;
  private final String location;

  public OperatorValidationFailure(String location, String field) {
    super("Invalid operator request");
    this.location = location;
    this.field = field;
  }

  public String field() {
    return field;
  }

  public String location() {
    return location;
  }
}
