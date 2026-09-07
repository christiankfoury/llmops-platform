package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "api_keys")
public class ApiKey extends BaseEntity {
  @Column(name = "application_id", nullable = false)
  private UUID applicationId;

  @Column(name = "key_prefix", nullable = false, length = 24)
  private String keyPrefix;

  @Column(name = "key_hash", nullable = false, length = 128)
  private String keyHash;

  @Column(name = "description", nullable = true, columnDefinition = "text")
  private String description;

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

  @Column(name = "last_used_at", nullable = true)
  private OffsetDateTime lastUsedAt;

  @Column(name = "revoked_at", nullable = true)
  private OffsetDateTime revokedAt;

  public UUID getApplicationId() {
    return applicationId;
  }

  public void setApplicationId(UUID value) {
    this.applicationId = value;
  }

  public String getKeyPrefix() {
    return keyPrefix;
  }

  public void setKeyPrefix(String value) {
    this.keyPrefix = value;
  }

  public String getKeyHash() {
    return keyHash;
  }

  public void setKeyHash(String value) {
    this.keyHash = value;
  }

  public String getDescription() {
    return description;
  }

  public void setDescription(String value) {
    this.description = value;
  }

  public Boolean getIsActive() {
    return isActive;
  }

  public void setIsActive(Boolean value) {
    this.isActive = value;
  }

  public OffsetDateTime getLastUsedAt() {
    return lastUsedAt;
  }

  public void setLastUsedAt(OffsetDateTime value) {
    this.lastUsedAt = value;
  }

  public OffsetDateTime getRevokedAt() {
    return revokedAt;
  }

  public void setRevokedAt(OffsetDateTime value) {
    this.revokedAt = value;
  }
}
