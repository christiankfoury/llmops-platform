package dev.christiankfoury.aiplatform.persistence;

import java.sql.Connection;
import java.sql.SQLException;
import org.flywaydb.core.Flyway;

/** All Java migration entrypoints use the same session lock as the guarded Alembic runner. */
public final class DatabaseMigrations {
  private DatabaseMigrations() {}

  public static void migrate(Flyway flyway) {
    locked(
        flyway,
        connection -> {
          String schema = schema(flyway, connection);
          if (hasTable(connection, schema, "alembic_version")
              && !hasTable(connection, schema, "flyway_schema_history")) {
            throw new IllegalStateException("Alembic database requires explicit verified adoption");
          }
          flyway.migrate();
        });
  }

  public static void adoptAlembic(Flyway flyway) {
    locked(
        flyway,
        connection -> {
          String schema = schema(flyway, connection);
          if (hasTable(connection, schema, "flyway_schema_history")) {
            throw new IllegalStateException("Flyway already owns this database schema");
          }
          if (!hasTable(connection, schema, "alembic_version")) {
            throw new IllegalStateException("An Alembic version marker is required for adoption");
          }
          connection.setSchema(schema);
          try (var statement = connection.createStatement();
              var rows = statement.executeQuery("SELECT version_num FROM alembic_version")) {
            if (!rows.next()
                || !"0002_external_telemetry".equals(rows.getString(1))
                || rows.next()) {
              throw new IllegalStateException("Alembic schema is not at the verified head");
            }
          }
          new SchemaContractVerifier().verify(connection, schema);
          if (!"1".equals(flyway.getConfiguration().getBaselineVersion().getVersion())) {
            throw new IllegalStateException("Only the verified V1 baseline can be adopted");
          }
          flyway.baseline();
          flyway.migrate();
        });
  }

  private static String schema(Flyway flyway, Connection connection) throws SQLException {
    String schema = flyway.getConfiguration().getDefaultSchema();
    if (schema == null) schema = connection.getSchema();
    SchemaContractVerifier.checkSchemaName(schema);
    return schema;
  }

  private static boolean hasTable(Connection connection, String schema, String table)
      throws SQLException {
    try (var query =
        connection.prepareStatement(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema=? AND table_name=?)")) {
      query.setString(1, schema);
      query.setString(2, table);
      try (var result = query.executeQuery()) {
        result.next();
        return result.getBoolean(1);
      }
    }
  }

  private static void locked(Flyway flyway, SqlAction action) {
    if (flyway.getConfiguration().isBaselineOnMigrate()
        || !flyway.getConfiguration().isCleanDisabled()) {
      throw new IllegalStateException("Unsafe Flyway baseline or clean configuration");
    }
    try (Connection connection = flyway.getConfiguration().getDataSource().getConnection()) {
      String schema = schema(flyway, connection);
      String previousSchema = connection.getSchema();
      String previousTimeout;
      try (var query = connection.createStatement();
          var rows = query.executeQuery("SHOW lock_timeout")) {
        rows.next();
        previousTimeout = rows.getString(1);
      }
      boolean acquired = false;
      try {
        setTimeout(connection, "5s");
        try (var lock =
            connection.prepareStatement(
                "SELECT pg_advisory_lock(hashtext(current_database()),hashtext(?))")) {
          lock.setString(1, schema);
          lock.execute();
          acquired = true;
        }
        action.run(connection);
      } finally {
        try {
          if (acquired) {
            try (var unlock =
                connection.prepareStatement(
                    "SELECT pg_advisory_unlock(hashtext(current_database()),hashtext(?))")) {
              unlock.setString(1, schema);
              unlock.execute();
            }
          }
        } finally {
          connection.setSchema(previousSchema);
          setTimeout(connection, previousTimeout);
        }
      }
    } catch (SQLException exception) {
      throw new IllegalStateException("Database migration operation failed", exception);
    }
  }

  private static void setTimeout(Connection connection, String value) throws SQLException {
    try (var statement = connection.prepareStatement("SELECT set_config('lock_timeout',?,false)")) {
      statement.setString(1, value);
      statement.execute();
    }
  }

  @FunctionalInterface
  private interface SqlAction {
    void run(Connection connection) throws SQLException;
  }
}
