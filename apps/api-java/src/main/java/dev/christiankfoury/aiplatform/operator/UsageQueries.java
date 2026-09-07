package dev.christiankfoury.aiplatform.operator;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true, timeout = 5)
public class UsageQueries {
  public record Summary(
      long requestCount, long errorCount, double averageLatencyMs, BigDecimal estimatedCostUsd) {}

  public record ApplicationScope(UUID id, String name, String slug, String environment) {}

  public record ProjectScope(
      UUID id, String name, String slug, List<ApplicationScope> applications) {}

  private final NamedParameterJdbcTemplate jdbc;

  public UsageQueries(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public Summary summary(UsageFilter filter) {
    return jdbc.queryForObject(
        """
        SELECT count(*) AS request_count, count(*) FILTER (WHERE r.status = 'failed') AS error_count,
          coalesce(avg(r.latency_ms), 0) AS average_latency_ms,
          coalesce(sum(c.estimated_cost_usd), 0) AS estimated_cost_usd
        FROM gateway_requests r LEFT JOIN cost_records c ON c.gateway_request_id = r.id
        """
            + filter.where(),
        filter.parameters(),
        (row, index) ->
            new Summary(
                row.getLong("request_count"),
                row.getLong("error_count"),
                row.getDouble("average_latency_ms"),
                row.getBigDecimal("estimated_cost_usd").setScale(6)));
  }

  public List<Map<String, Object>> requests(UsageFilter filter) {
    return jdbc.query(
        """
        SELECT r.id, r.request_id, r.project_id, p.name AS project_name, p.slug AS project_slug,
          r.application_id, a.name AS application_name, a.slug AS application_slug,
          a.environment AS application_environment, r.prompt_version_id, r.model_route_id,
          r.status, r.provider, r.model_name, r.latency_ms, r.estimated_input_tokens,
          r.estimated_output_tokens, r.estimated_cost_usd, r.error_category,
          r.source_app, r.operation_type, r.external_event_id, r.external_request_id, r.created_at
        FROM gateway_requests r LEFT JOIN projects p ON p.id = r.project_id
          LEFT JOIN applications a ON a.id = r.application_id
        """
            + filter.where()
            + " ORDER BY r.created_at DESC, r.id DESC LIMIT :limit",
        filter.parameters(),
        (row, index) -> {
          Map<String, Object> result = new LinkedHashMap<>();
          var columns = row.getMetaData();
          for (int column = 1; column <= columns.getColumnCount(); column++) {
            String name = columns.getColumnLabel(column);
            result.put(
                name,
                name.equals("created_at")
                    ? row.getObject(column, OffsetDateTime.class)
                    : row.getObject(column));
          }
          return result;
        });
  }

  public List<ProjectScope> scopes() {
    return jdbc.query(
        """
        SELECT p.id, p.name, p.slug, a.id AS app_id, a.name AS app_name,
          a.slug AS app_slug, a.environment
        FROM projects p LEFT JOIN applications a ON a.project_id = p.id AND a.is_active = true
        WHERE p.is_active = true ORDER BY p.name, p.id, a.name, a.id
        """,
        Map.of(),
        rows -> {
          Map<UUID, ProjectScope> projects = new LinkedHashMap<>();
          while (rows.next()) {
            UUID id = rows.getObject("id", UUID.class);
            ProjectScope project = projects.get(id);
            if (project == null) {
              project =
                  new ProjectScope(
                      id, rows.getString("name"), rows.getString("slug"), new ArrayList<>());
              projects.put(id, project);
            }
            UUID applicationId = rows.getObject("app_id", UUID.class);
            if (applicationId != null)
              project
                  .applications()
                  .add(
                      new ApplicationScope(
                          applicationId,
                          rows.getString("app_name"),
                          rows.getString("app_slug"),
                          rows.getString("environment")));
          }
          return projects.values().stream()
              .map(
                  project ->
                      new ProjectScope(
                          project.id(),
                          project.name(),
                          project.slug(),
                          List.copyOf(project.applications())))
              .toList();
        });
  }
}
