package dev.christiankfoury.aiplatform.security;

import java.time.Clock;
import java.time.Instant;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.jwt.Jwt;

public final class OperatorTokenValidator implements OAuth2TokenValidator<Jwt> {
  private final String audience;
  private final Clock clock;

  public OperatorTokenValidator(String audience, Clock clock) {
    this.audience = audience;
    this.clock = clock;
  }

  @Override
  public OAuth2TokenValidatorResult validate(Jwt token) {
    Instant now = clock.instant();
    String subject = token.getSubject();
    boolean valid =
        subject != null
            && !subject.isBlank()
            && subject.codePointCount(0, subject.length()) <= 255
            && subject
                .codePoints()
                .noneMatch(c -> Character.isISOControl(c) || c >= 0xd800 && c <= 0xdfff)
            && token.getAudience() != null
            && token.getAudience().contains(audience)
            && token.getExpiresAt() != null
            && token.getIssuedAt() != null
            && token.getExpiresAt().isAfter(token.getIssuedAt())
            && !token.getIssuedAt().isAfter(now.plusSeconds(30));
    // Cognito labels token purpose; other OIDC providers may omit this provider-specific claim.
    Object purpose = token.getClaim("token_use");
    if (purpose != null && !purpose.equals("access")) valid = false;
    return valid
        ? OAuth2TokenValidatorResult.success()
        : OAuth2TokenValidatorResult.failure(
            new OAuth2Error("invalid_token", "Invalid operator token", null));
  }
}
