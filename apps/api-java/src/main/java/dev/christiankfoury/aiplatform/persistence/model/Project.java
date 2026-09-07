package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;

@Entity
@Table(name = "projects")
public class Project extends BaseEntity {
  @Column(name = "name", nullable = false, length = 160)
  private String name;

  @Column(name = "slug", nullable = false, length = 120)
  private String slug;

  @Column(name = "description", nullable = true, columnDefinition = "text")
  private String description;

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

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
}
