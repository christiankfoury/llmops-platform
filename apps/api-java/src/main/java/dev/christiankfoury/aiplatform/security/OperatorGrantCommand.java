package dev.christiankfoury.aiplatform.security;

import dev.christiankfoury.aiplatform.persistence.SchemaContractVerifier;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.UUID;

/** Explicit database-owner provisioning; never exposed as an HTTP self-service grant. */
public final class OperatorGrantCommand {
  private OperatorGrantCommand() {}

  public static void execute(
      Connection connection,
      String schema,
      String issuer,
      String subject,
      String projectSlug,
      String role,
      boolean revoke)
      throws SQLException {
    SchemaContractVerifier.checkSchemaName(schema);
    new OperatorSecuritySettings("oidc", issuer, "grant-bootstrap", issuer, "production");
    if (subject == null
        || subject.isBlank()
        || subject.codePointCount(0, subject.length()) > 255
        || subject
            .codePoints()
            .anyMatch(c -> Character.isISOControl(c) || c >= 0xd800 && c <= 0xdfff)
        || projectSlug == null
        || projectSlug.isBlank()
        || projectSlug.length() > 100
        || !(role.equals("viewer") || role.equals("operator")))
      throw new IllegalArgumentException("Invalid operator grant settings");
    if (!connection.getAutoCommit())
      throw new IllegalArgumentException("A dedicated connection is required");
    String previousSchema = connection.getSchema();
    connection.setSchema(schema);
    connection.setAutoCommit(false);
    try {
      try (var statement = connection.createStatement()) {
        statement.execute("SET LOCAL lock_timeout = '5s'");
        statement.execute("SET LOCAL statement_timeout = '5s'");
        try (var rows =
            statement.executeQuery(
                "SELECT count(*) FROM flyway_schema_history WHERE version='2' AND success")) {
          rows.next();
          if (rows.getInt(1) != 1)
            throw new IllegalArgumentException("Apply the operator grant migration first");
        }
      }
      UUID project;
      try (var statement =
          connection.prepareStatement(
              "SELECT id FROM projects WHERE slug=? AND (is_active=true OR ?) FOR UPDATE")) {
        statement.setString(1, projectSlug);
        statement.setBoolean(2, revoke);
        try (var rows = statement.executeQuery()) {
          if (!rows.next()) throw new IllegalArgumentException("Active project not found");
          project = rows.getObject(1, UUID.class);
        }
      }
      UUID grantId;
      try (var statement =
          connection.prepareStatement(
              """
          INSERT INTO operator_project_grants (id, issuer, subject, project_id, role, is_active, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
          ON CONFLICT ON CONSTRAINT uq_operator_project_grants_identity_project
          DO UPDATE SET role=excluded.role, is_active=excluded.is_active, updated_at=CURRENT_TIMESTAMP
          RETURNING id
          """)) {
        statement.setObject(1, UUID.randomUUID());
        statement.setString(2, issuer);
        statement.setString(3, subject);
        statement.setObject(4, project);
        statement.setString(5, role);
        statement.setBoolean(6, !revoke);
        try (var rows = statement.executeQuery()) {
          rows.next();
          grantId = rows.getObject(1, UUID.class);
        }
      }
      try (var statement =
          connection.prepareStatement(
              """
          INSERT INTO audit_logs (id, project_id, actor_type, actor_id, action, resource_type, resource_id, metadata_json,
                                  created_at, updated_at)
          VALUES (?, ?, 'database_owner', 'database:' || session_user, ?, 'operator_project_grant', ?,
                  jsonb_build_object('role', CAST(? AS text), 'is_active', CAST(? AS boolean)), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
          """)) {
        statement.setObject(1, UUID.randomUUID());
        statement.setObject(2, project);
        statement.setString(3, revoke ? "operator_grant.revoke" : "operator_grant.upsert");
        statement.setString(4, grantId.toString());
        statement.setString(5, role);
        statement.setBoolean(6, !revoke);
        statement.executeUpdate();
      }
      connection.commit();
    } catch (SQLException | RuntimeException failure) {
      connection.rollback();
      throw failure;
    } finally {
      connection.setAutoCommit(true);
      connection.setSchema(previousSchema);
    }
  }
}
