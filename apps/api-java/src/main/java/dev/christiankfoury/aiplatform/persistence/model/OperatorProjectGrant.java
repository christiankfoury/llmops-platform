package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "operator_project_grants")
public class OperatorProjectGrant extends BaseEntity {
  @Column(nullable = false, length = 512)
  private String issuer;

  @Column(nullable = false, length = 255)
  private String subject;

  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(nullable = false, length = 16)
  private String role;

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

  public String getIssuer() {
    return issuer;
  }

  public void setIssuer(String value) {
    issuer = value;
  }

  public String getSubject() {
    return subject;
  }

  public void setSubject(String value) {
    subject = value;
  }

  public UUID getProjectId() {
    return projectId;
  }

  public void setProjectId(UUID value) {
    projectId = value;
  }

  public String getRole() {
    return role;
  }

  public void setRole(String value) {
    role = value;
  }

  public Boolean getIsActive() {
    return isActive;
  }

  public void setIsActive(Boolean value) {
    isActive = value;
  }
}
