package dev.christiankfoury.aiplatform.auth;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.persistence.repository.ApiKeyRepository;
import dev.christiankfoury.aiplatform.persistence.repository.ClientApplicationRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ApplicationAuthenticator {
  public record Scope(UUID keyId, UUID applicationId, UUID projectId) {}

  private final ApiKeyRepository keys;
  private final ClientApplicationRepository applications;

  public ApplicationAuthenticator(ApiKeyRepository keys, ClientApplicationRepository applications) {
    this.keys = keys;
    this.applications = applications;
  }

  @Transactional(readOnly = true)
  public Scope authenticate(String value) {
    if (value == null || value.isEmpty()) throw new ApiFailure(401, "Missing API key");
    if (value.length() > 512) throw new ApiFailure(401, "Invalid API key");
    var key =
        keys.findByKeyHash(hash(value))
            .filter(item -> Boolean.TRUE.equals(item.getIsActive()) && item.getRevokedAt() == null)
            .orElseThrow(() -> new ApiFailure(401, "Invalid API key"));
    var application =
        applications
            .findById(key.getApplicationId())
            .filter(item -> Boolean.TRUE.equals(item.getIsActive()))
            .orElseThrow(
                () -> new ApiFailure(401, "API key is not attached to an active application"));
    return new Scope(key.getId(), application.getId(), application.getProjectId());
  }

  public static String hash(String value) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }
}
