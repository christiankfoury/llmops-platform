package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "applications")
public class ClientApplication extends BaseEntity {
  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(name = "name", nullable = false, length = 160)
  private String name;

  @Column(name = "slug", nullable = false, length = 120)
  private String slug;

  @Column(name = "environment", nullable = false, length = 40)
  private String environment = "local";

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

  public UUID getProjectId() {
    return projectId;
  }

  public void setProjectId(UUID value) {
    this.projectId = value;
  }

  public String getName() {
    return name;
  }

  public void setName(String value) {
    this.name = value;
  }

  public String getSlug() {
    return slug;
  }

  public void setSlug(String value) {
    this.slug = value;
  }

  public String getEnvironment() {
    return environment;
  }

  public void setEnvironment(String value) {
    this.environment = value;
  }

  public Boolean getIsActive() {
    return isActive;
  }

  public void setIsActive(Boolean value) {
    this.isActive = value;
  }
}
