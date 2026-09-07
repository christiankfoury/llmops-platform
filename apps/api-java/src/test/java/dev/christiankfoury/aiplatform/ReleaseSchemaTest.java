package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.christiankfoury.aiplatform.persistence.DatabaseMigrations;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;

class ReleaseSchemaTest extends PostgresTestSupport {
  private Flyway database() throws Exception {
    String schema = "release_" + UUID.randomUUID().toString().replace("-", "");
    try (var connection = POSTGRES.getPostgresDatabase().getConnection();
        var statement = connection.createStatement()) {
      statement.execute("CREATE SCHEMA " + schema);
    }
    return Flyway.configure()
        .dataSource(POSTGRES.getPostgresDatabase())
        .schemas(schema)
        .defaultSchema(schema)
        .baselineOnMigrate(false)
        .cleanDisabled(true)
        .load();
  }

  private List<String> history(Flyway flyway) throws Exception {
    var result = new ArrayList<String>();
    try (var connection = POSTGRES.getPostgresDatabase().getConnection()) {
      connection.setSchema(flyway.getConfiguration().getDefaultSchema());
      try (var statement = connection.createStatement();
          var rows =
              statement.executeQuery(
                  "SELECT row_to_json(h)::text FROM (SELECT * FROM flyway_schema_history ORDER BY installed_rank) h")) {
        while (rows.next()) result.add(rows.getString(1));
      }
    }
    return result;
  }

  @Test
  void compatibleSchemaIsVerifiedWithoutHistoryWrites() throws Exception {
    Flyway flyway = database();
    DatabaseMigrations.migrate(flyway);
    var before = history(flyway);
    DatabaseMigrations.verifySchema(flyway, "2");
    assertThat(history(flyway)).isEqualTo(before);
  }

  @Test
  void missingHistoryAndWrongTargetNeverTriggerMigration() throws Exception {
    Flyway flyway = database();
    assertThatThrownBy(() -> DatabaseMigrations.verifySchema(flyway, "2"))
        .hasMessageContaining("history is required");
    assertThat(flyway.info().applied()).isEmpty();
    DatabaseMigrations.migrate(flyway);
    var before = history(flyway);
    assertThatThrownBy(() -> DatabaseMigrations.verifySchema(flyway, "1"))
        .hasMessageContaining("incompatible");
    assertThatThrownBy(() -> DatabaseMigrations.verifySchema(flyway, "2;invalid"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(history(flyway)).isEqualTo(before);
  }

  @Test
  void newerOrChangedDatabaseHistoryIsRejectedWithoutRepairOrDowngrade() throws Exception {
    Flyway flyway = database();
    DatabaseMigrations.migrate(flyway);
    try (var connection = POSTGRES.getPostgresDatabase().getConnection()) {
      connection.setSchema(flyway.getConfiguration().getDefaultSchema());
      try (var statement = connection.createStatement()) {
        statement.executeUpdate("UPDATE flyway_schema_history SET version='3' WHERE version='2'");
        var newer = history(flyway);
        assertThatThrownBy(() -> DatabaseMigrations.verifySchema(flyway, "2"))
            .hasMessageContaining("incompatible");
        assertThat(history(flyway)).isEqualTo(newer);
        statement.executeUpdate(
            "UPDATE flyway_schema_history SET version='2', checksum=checksum+1 WHERE version='3'");
        var changed = history(flyway);
        assertThatThrownBy(() -> DatabaseMigrations.verifySchema(flyway, "2"))
            .isInstanceOf(org.flywaydb.core.api.exception.FlywayValidateException.class);
        assertThat(history(flyway)).isEqualTo(changed);
      }
    }
  }
}
