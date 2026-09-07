package dev.christiankfoury.aiplatform.persistence.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "gateway_requests")
public class GatewayRequest extends BaseEntity {
  @Column(name = "request_id", nullable = false, length = 80)
  private String requestId;

  @Column(name = "project_id", nullable = false)
  private UUID projectId;

  @Column(name = "application_id", nullable = false)
  private UUID applicationId;

  @Column(name = "api_key_id", nullable = true)
  private UUID apiKeyId;

  @Column(name = "prompt_version_id", nullable = true)
  private UUID promptVersionId;

  @Column(name = "model_route_id", nullable = true)
  private UUID modelRouteId;

  @Column(name = "provider", nullable = true, length = 80)
  private String provider;

  @Column(name = "model_name", nullable = true, length = 160)
  private String modelName;

  @Column(name = "status", nullable = false, length = 40)
  private String status = "received";

  @Column(name = "latency_ms", nullable = true)
  private Integer latencyMs;

  @Column(name = "estimated_input_tokens", nullable = true)
  private Integer estimatedInputTokens;

  @Column(name = "estimated_output_tokens", nullable = true)
  private Integer estimatedOutputTokens;

  @Column(name = "estimated_cost_usd", nullable = true, precision = 12, scale = 6)
  private BigDecimal estimatedCostUsd;

  @Column(name = "error_category", nullable = true, length = 80)
  private String errorCategory;

  @Column(name = "source_app", nullable = true, length = 80)
  private String sourceApp;

  @Column(name = "operation_type", nullable = true, length = 80)
  private String operationType;

  @Column(name = "external_event_id", nullable = true, length = 80)
  private String externalEventId;

  @Column(name = "external_request_id", nullable = true, length = 120)
  private String externalRequestId;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "external_metadata_json", nullable = true, columnDefinition = "jsonb")
  private Map<String, Object> externalMetadataJson;

  public String getRequestId() {
    return requestId;
  }

  public void setRequestId(String value) {
    this.requestId = value;
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

  public UUID getApiKeyId() {
    return apiKeyId;
  }

  public void setApiKeyId(UUID value) {
    this.apiKeyId = value;
  }

  public UUID getPromptVersionId() {
    return promptVersionId;
  }

  public void setPromptVersionId(UUID value) {
    this.promptVersionId = value;
  }

  public UUID getModelRouteId() {
    return modelRouteId;
  }

  public void setModelRouteId(UUID value) {
    this.modelRouteId = value;
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

  public String getStatus() {
    return status;
  }

  public void setStatus(String value) {
    this.status = value;
  }

  public Integer getLatencyMs() {
    return latencyMs;
  }

  public void setLatencyMs(Integer value) {
    this.latencyMs = value;
  }

  public Integer getEstimatedInputTokens() {
    return estimatedInputTokens;
  }

  public void setEstimatedInputTokens(Integer value) {
    this.estimatedInputTokens = value;
  }

  public Integer getEstimatedOutputTokens() {
    return estimatedOutputTokens;
  }

  public void setEstimatedOutputTokens(Integer value) {
    this.estimatedOutputTokens = value;
  }

  public BigDecimal getEstimatedCostUsd() {
    return estimatedCostUsd;
  }

  public void setEstimatedCostUsd(BigDecimal value) {
    this.estimatedCostUsd = value;
  }

  public String getErrorCategory() {
    return errorCategory;
  }

  public void setErrorCategory(String value) {
    this.errorCategory = value;
  }

  public String getSourceApp() {
    return sourceApp;
  }

  public void setSourceApp(String value) {
    this.sourceApp = value;
  }

  public String getOperationType() {
    return operationType;
  }

  public void setOperationType(String value) {
    this.operationType = value;
  }

  public String getExternalEventId() {
    return externalEventId;
  }

  public void setExternalEventId(String value) {
    this.externalEventId = value;
  }

  public String getExternalRequestId() {
    return externalRequestId;
  }

  public void setExternalRequestId(String value) {
    this.externalRequestId = value;
  }

  public Map<String, Object> getExternalMetadataJson() {
    return externalMetadataJson;
  }

  public void setExternalMetadataJson(Map<String, Object> value) {
    this.externalMetadataJson = value;
  }
}
