package dev.christiankfoury.aiplatform.security;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true, timeout = 5)
public class OperatorAuthorization {
  public record Grant(UUID projectId, String role) {}

  private final NamedParameterJdbcTemplate jdbc;

  public OperatorAuthorization(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public List<Grant> grants() {
    var identity = OperatorIdentity.current();
    return jdbc.query(
        """
        SELECT g.project_id, g.role FROM operator_project_grants g
          JOIN projects p ON p.id = g.project_id
        WHERE g.issuer = :issuer AND g.subject = :subject AND g.is_active = true
          AND p.is_active = true AND g.role IN ('viewer', 'operator')
        ORDER BY g.project_id
        """,
        Map.of("issuer", identity.issuer(), "subject", identity.subject()),
        (row, index) -> new Grant(row.getObject("project_id", UUID.class), row.getString("role")));
  }

  public Set<UUID> projects(boolean write) {
    return grants().stream()
        .filter(grant -> !write || grant.role().equals("operator"))
        .map(Grant::projectId)
        .collect(Collectors.toUnmodifiableSet());
  }

  public void requireResource(UUID projectId, boolean write) {
    if (!projects(write).contains(projectId)) throw new ApiFailure(404, "Resource not found");
  }
}
