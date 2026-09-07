package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "model_routes")
public class ModelRoute extends BaseEntity {
  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(name = "application_id", nullable = true)
  private UUID applicationId;

  @Column(name = "environment", nullable = false, length = 40)
  private String environment = "local";

  @Column(name = "provider", nullable = false, length = 80)
  private String provider;

  @Column(name = "model_name", nullable = false, length = 160)
  private String modelName;

  @Column(name = "priority", nullable = false)
  private Integer priority = 100;

  @Column(name = "is_default", nullable = false)
  private Boolean isDefault = false;

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

  public UUID getProjectId() {
    return projectId;
  }

  public void setProjectId(UUID value) {
    this.projectId = value;
  }

  public UUID getApplicationId() {
    return applicationId;
  }

  public void setApplicationId(UUID value) {
    this.applicationId = value;
  }

  public String getEnvironment() {
    return environment;
  }

  public void setEnvironment(String value) {
    this.environment = value;
  }

  public String getProvider() {
    return provider;
  }

  public void setProvider(String value) {
    this.provider = value;
  }

  public String getModelName() {
    return modelName;
  }

  public void setModelName(String value) {
    this.modelName = value;
  }

  public Integer getPriority() {
    return priority;
  }

  public void setPriority(Integer value) {
    this.priority = value;
  }

  public Boolean getIsDefault() {
    return isDefault;
  }

  public void setIsDefault(Boolean value) {
    this.isDefault = value;
  }

  public Boolean getIsActive() {
    return isActive;
  }

  public void setIsActive(Boolean value) {
    this.isActive = value;
  }
}
