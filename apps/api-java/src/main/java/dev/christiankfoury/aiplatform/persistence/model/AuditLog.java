package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "audit_logs")
public class AuditLog extends BaseEntity {
  @Column(name = "project_id", nullable = true)
  private UUID projectId;

  @Column(name = "application_id", nullable = true)
  private UUID applicationId;

  @Column(name = "actor_type", nullable = false, length = 40)
  private String actorType;

  @Column(name = "actor_id", nullable = true, length = 120)
  private String actorId;

  @Column(name = "action", nullable = false, length = 120)
  private String action;

  @Column(name = "resource_type", nullable = false, length = 80)
  private String resourceType;

  @Column(name = "resource_id", nullable = true, length = 120)
  private String resourceId;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
  private Map<String, Object> metadataJson = new LinkedHashMap<>();

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

  public String getActorType() {
    return actorType;
  }

  public void setActorType(String value) {
    this.actorType = value;
  }

  public String getActorId() {
    return actorId;
  }

  public void setActorId(String value) {
    this.actorId = value;
  }

  public String getAction() {
    return action;
  }

  public void setAction(String value) {
    this.action = value;
  }

  public String getResourceType() {
    return resourceType;
  }

  public void setResourceType(String value) {
    this.resourceType = value;
  }

  public String getResourceId() {
    return resourceId;
  }

  public void setResourceId(String value) {
    this.resourceId = value;
  }

  public Map<String, Object> getMetadataJson() {
    return metadataJson;
  }

  public void setMetadataJson(Map<String, Object> value) {
    this.metadataJson = value;
  }
}
