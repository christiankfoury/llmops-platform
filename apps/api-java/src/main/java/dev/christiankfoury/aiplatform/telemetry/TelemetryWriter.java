package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator.Scope;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.persistence.model.CostRecord;
import dev.christiankfoury.aiplatform.persistence.repository.CostRecordRepository;
import dev.christiankfoury.aiplatform.persistence.repository.GatewayRequestRepository;
import java.sql.Types;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

@Service
public class TelemetryWriter {
  private final NamedParameterJdbcTemplate jdbc;
  private final GatewayRequestRepository requests;
  private final CostRecordRepository costs;
  private final JsonMapper json;
  private final dev.christiankfoury.aiplatform.security.KeyUsageRecorder keyUsage;

  public TelemetryWriter(
      NamedParameterJdbcTemplate jdbc,
      GatewayRequestRepository requests,
      CostRecordRepository costs,
      JsonMapper json,
      dev.christiankfoury.aiplatform.security.KeyUsageRecorder keyUsage) {
    this.jdbc = jdbc;
    this.requests = requests;
    this.costs = costs;
    this.json = json;
    this.keyUsage = keyUsage;
  }

  @Transactional(timeout = 5)
  public TelemetryResponse write(Scope scope, TelemetryEvent event) {
    UUID id = UUID.randomUUID();
    var parameters =
        new MapSqlParameterSource()
            .addValue("id", id)
            .addValue("requestId", "ext_" + UUID.randomUUID().toString().replace("-", ""))
            .addValue("project", scope.projectId())
            .addValue("application", scope.applicationId())
            .addValue("key", scope.keyId())
            .addValue("source", event.text("source_app"))
            .addValue("operation", event.text("operation_type"))
            .addValue("event", event.text("event_id"))
            .addValue("externalRequest", event.text("external_request_id"))
            .addValue("provider", event.text("provider"))
            .addValue("model", event.text("model"))
            .addValue("status", event.text("status"))
            .addValue("latency", event.integer("latency_ms"))
            .addValue("input", event.integer("input_tokens"))
            .addValue("output", event.integer("output_tokens"))
            .addValue("cost", event.cost())
            .addValue("error", event.text("error_category"))
            .addValue("metadata", json.writeValueAsString(event.persistedMetadata()))
            .addValue("at", event.occurredAt(), Types.TIMESTAMP_WITH_TIMEZONE);
    // PostgreSQL serializes concurrent conflicts without aborting the transaction or logging
    // payloads.
    // JpaTransactionManager exposes the same JDBC connection to this template and the cost
    // repository.
    int inserted =
        jdbc.update(
            """
        INSERT INTO gateway_requests (id, request_id, project_id, application_id, api_key_id,
          source_app, operation_type, external_event_id, external_request_id, provider, model_name,
          status, latency_ms, estimated_input_tokens, estimated_output_tokens, estimated_cost_usd,
          error_category, external_metadata_json, created_at, updated_at)
        VALUES (:id, :requestId, :project, :application, :key, :source, :operation, :event,
          :externalRequest, :provider, :model, :status, :latency, :input, :output, :cost,
          :error, CAST(:metadata AS jsonb), :at, :at)
        ON CONFLICT ON CONSTRAINT uq_gateway_requests_application_external_event DO NOTHING
        """,
            parameters);
    var request =
        requests
            .findByApplicationIdAndExternalEventId(scope.applicationId(), event.text("event_id"))
            .orElseThrow(() -> new IllegalStateException("Telemetry write could not be read"));
    keyUsage.record(scope.keyId());
    if (inserted == 0) {
      var metadata = request.getExternalMetadataJson();
      if (metadata == null || !event.fingerprint().equals(metadata.get("payload_fingerprint")))
        throw new ApiFailure(
            409, "Event ID already exists with a different or unverifiable payload");
      return TelemetryResponse.from(request, true);
    }
    if (event.cost() != null) {
      CostRecord cost = new CostRecord();
      cost.setGatewayRequestId(id);
      cost.setProjectId(scope.projectId());
      cost.setApplicationId(scope.applicationId());
      cost.setProvider(event.text("provider"));
      cost.setModelName(event.text("model"));
      cost.setInputTokens(
          event.integer("input_tokens") == null ? 0 : event.integer("input_tokens"));
      cost.setOutputTokens(
          event.integer("output_tokens") == null ? 0 : event.integer("output_tokens"));
      cost.setEstimatedCostUsd(event.cost());
      cost.setCurrency(event.text("currency"));
      cost.setCreatedAt(event.occurredAt());
      cost.setUpdatedAt(event.occurredAt());
      costs.saveAndFlush(cost);
    }
    return TelemetryResponse.from(request, false);
  }
}
