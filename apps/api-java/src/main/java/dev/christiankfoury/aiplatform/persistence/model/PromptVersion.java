package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "prompt_versions")
public class PromptVersion extends BaseEntity {
  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(name = "application_id", nullable = true)
  private UUID applicationId;

  @Column(name = "name", nullable = false, length = 160)
  private String name;

  @Column(name = "version", nullable = false)
  private Integer version;

  @Column(name = "content", nullable = false, columnDefinition = "text")
  private String content;

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

  public String getName() {
    return name;
  }

  public void setName(String value) {
    this.name = value;
  }

  public Integer getVersion() {
    return version;
  }

  public void setVersion(Integer value) {
    this.version = value;
  }

  public String getContent() {
    return content;
  }

  public void setContent(String value) {
    this.content = value;
  }

  public Boolean getIsActive() {
    return isActive;
  }

  public void setIsActive(Boolean value) {
    this.isActive = value;
  }
}
