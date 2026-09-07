package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "cost_records")
public class CostRecord extends BaseEntity {
  @Column(name = "gateway_request_id", nullable = false)
  private UUID gatewayRequestId;

  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(name = "application_id", nullable = false)
  private UUID applicationId;

  @Column(name = "provider", nullable = false, length = 80)
  private String provider;

  @Column(name = "model_name", nullable = false, length = 160)
  private String modelName;

  @Column(name = "input_tokens", nullable = false)
  private Integer inputTokens = 0;

  @Column(name = "output_tokens", nullable = false)
  private Integer outputTokens = 0;

  @Column(name = "estimated_cost_usd", nullable = false, precision = 12, scale = 6)
  private BigDecimal estimatedCostUsd;

  @Column(name = "currency", nullable = false, length = 3)
  private String currency = "USD";

  public UUID getGatewayRequestId() {
    return gatewayRequestId;
  }

  public void setGatewayRequestId(UUID value) {
    this.gatewayRequestId = value;
  }

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

  public Integer getInputTokens() {
    return inputTokens;
  }

  public void setInputTokens(Integer value) {
    this.inputTokens = value;
  }

  public Integer getOutputTokens() {
    return outputTokens;
  }

  public void setOutputTokens(Integer value) {
    this.outputTokens = value;
  }

  public BigDecimal getEstimatedCostUsd() {
    return estimatedCostUsd;
  }

  public void setEstimatedCostUsd(BigDecimal value) {
    this.estimatedCostUsd = value;
  }

  public String getCurrency() {
    return currency;
  }

  public void setCurrency(String value) {
    this.currency = value;
  }
}
