package dev.christiankfoury.aiplatform.security;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;

public record OperatorIdentity(String issuer, String subject) {
  public static OperatorIdentity current() {
    var authentication = SecurityContextHolder.getContext().getAuthentication();
    if (authentication == null
        || !authentication.isAuthenticated()
        || !(authentication.getPrincipal() instanceof Jwt jwt)
        || jwt.getIssuer() == null
        || jwt.getSubject() == null) throw new ApiFailure(401, "Unauthorized");
    return new OperatorIdentity(jwt.getIssuer().toString(), jwt.getSubject());
  }

  public String actorId() {
    return "oidc:" + ApplicationAuthenticator.hash(issuer + "\n" + subject);
  }

  @Override
  public String toString() {
    return "OperatorIdentity[verified identity omitted]";
  }
}
