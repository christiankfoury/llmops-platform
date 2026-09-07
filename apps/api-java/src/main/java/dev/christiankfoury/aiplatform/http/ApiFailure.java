package dev.christiankfoury.aiplatform.http;

/** Only fixed, application-owned messages may cross this HTTP boundary. */
public final class ApiFailure extends RuntimeException {
  private static final long serialVersionUID = 1L;
  private final int status;

  public ApiFailure(int status, String safeDetail) {
    super(safeDetail);
    this.status = status;
  }

  public int status() {
    return status;
  }
}
