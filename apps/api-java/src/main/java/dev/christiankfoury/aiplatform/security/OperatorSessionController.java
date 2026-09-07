package dev.christiankfoury.aiplatform.security;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OperatorSessionController {
  public record Session(
      boolean authenticated, String actorId, List<OperatorAuthorization.Grant> projects) {}

  private final OperatorAuthorization authorization;

  public OperatorSessionController(OperatorAuthorization authorization) {
    this.authorization = authorization;
  }

  @GetMapping("/v1/operator/me")
  public Session current() {
    return new Session(true, OperatorIdentity.current().actorId(), authorization.grants());
  }
}
