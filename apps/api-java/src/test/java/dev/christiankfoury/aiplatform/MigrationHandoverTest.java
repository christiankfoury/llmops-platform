package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.christiankfoury.aiplatform.persistence.DatabaseMigrations;
import dev.christiankfoury.aiplatform.persistence.SchemaContractVerifier;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class MigrationHandoverTest extends PostgresTestSupport {
  private final SchemaContractVerifier verifier = new SchemaContractVerifier();

  @Test
  void freshAndAdoptedSchemasMatchAndKeepAllLegacyRows() throws Exception {
    String fresh = createSchema(false);
    String legacy = createSchema(true);
    DatabaseMigrations.migrate(flyway(fresh));
    try (Connection connection = connection(legacy)) {
      try (var input = getClass().getResourceAsStream("/legacy-fixture.sql");
          var statement = connection.createStatement()) {
        if (input == null) throw new IllegalStateException("Legacy fixture is missing");
        statement.execute(new String(input.readAllBytes(), StandardCharsets.UTF_8));
      }
      Map<String, List<String>> before = rows(connection, legacy);
      DatabaseMigrations.adoptAlembic(flyway(legacy));
      assertThat(rows(connection, legacy)).isEqualTo(before);
      verifier.verify(connection, legacy);
      try (Connection freshConnection = connection(fresh)) {
        verifier.verify(freshConnection, fresh);
        assertThat(verifier.inspect(freshConnection, fresh))
            .isEqualTo(verifier.inspect(connection, legacy));
      }
      try (var statement = connection.createStatement();
          var versions = statement.executeQuery("SELECT version_num FROM alembic_version")) {
        assertThat(versions.next()).isTrue();
        assertThat(versions.getString(1)).isEqualTo("0002_external_telemetry");
      }
      DatabaseMigrations.migrate(flyway(legacy));
      assertThat(rows(connection, legacy)).isEqualTo(before);
      assertThatThrownBy(() -> DatabaseMigrations.adoptAlembic(flyway(legacy)))
          .isInstanceOf(IllegalStateException.class);
    }
  }

  @Test
  void implicitAdoptionAndWrongVersionAreRefusedWithoutHistoryWrites() throws Exception {
    String legacy = createSchema(true);
    assertThatThrownBy(() -> DatabaseMigrations.migrate(flyway(legacy)))
        .hasMessageContaining("explicit verified adoption");
    try (Connection connection = connection(legacy);
        var statement = connection.createStatement()) {
      statement.executeUpdate("UPDATE alembic_version SET version_num='unverified_head'");
      assertThatThrownBy(() -> DatabaseMigrations.adoptAlembic(flyway(legacy)))
          .hasMessageContaining("verified head");
      assertNoFlywayHistory(connection, legacy);
    }
  }

  @Test
  void schemaDriftAndUnsafeConfigurationCannotBeBaselined() throws Exception {
    String legacy = createSchema(true);
    try (Connection connection = connection(legacy);
        var statement = connection.createStatement()) {
      // Only this test's newly created empty schema is altered.
      statement.execute(
          "ALTER TABLE cost_records ALTER COLUMN estimated_cost_usd TYPE numeric(10,2)");
      assertThatThrownBy(() -> DatabaseMigrations.adoptAlembic(flyway(legacy)))
          .hasMessageContaining("cost_records");
      assertNoFlywayHistory(connection, legacy);
    }
    Flyway unsafe =
        Flyway.configure()
            .dataSource(POSTGRES.getPostgresDatabase())
            .schemas(legacy)
            .defaultSchema(legacy)
            .baselineOnMigrate(true)
            .cleanDisabled(true)
            .load();
    assertThatThrownBy(() -> DatabaseMigrations.adoptAlembic(unsafe))
        .hasMessageContaining("Unsafe Flyway");
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "ALTER TABLE projects ALTER COLUMN created_at TYPE timestamp(3) with time zone",
        "ALTER TABLE applications DROP CONSTRAINT applications_project_id_fkey; ALTER TABLE applications ADD FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE",
        "DROP INDEX ix_projects_slug; CREATE INDEX ix_projects_slug ON projects(slug DESC)",
        "ALTER TABLE projects ALTER COLUMN slug TYPE varchar(100) COLLATE \"C\""
      })
  void subtleSchemaDriftIsRefused(String change) throws Exception {
    String legacy = createSchema(true);
    try (Connection connection = connection(legacy);
        var statement = connection.createStatement()) {
      statement.execute(change);
      assertThatThrownBy(() -> DatabaseMigrations.adoptAlembic(flyway(legacy)))
          .isInstanceOf(IllegalStateException.class);
      assertNoFlywayHistory(connection, legacy);
    }
  }

  private String createSchema(boolean legacy) throws Exception {
    String schema = "contract_" + UUID.randomUUID().toString().replace("-", "");
    try (Connection connection = POSTGRES.getPostgresDatabase().getConnection();
        var statement = connection.createStatement()) {
      statement.execute("CREATE SCHEMA " + schema);
      connection.setSchema(schema);
      if (legacy) {
        try (var input = getClass().getResourceAsStream("/contracts/alembic-schema.sql")) {
          if (input == null) throw new IllegalStateException("Legacy SQL is missing");
          statement.execute(new String(input.readAllBytes(), StandardCharsets.UTF_8));
        }
      }
    }
    return schema;
  }

  private Connection connection(String schema) throws Exception {
    Connection connection = POSTGRES.getPostgresDatabase().getConnection();
    connection.setSchema(schema);
    return connection;
  }

  private Flyway flyway(String schema) {
    return Flyway.configure()
        .dataSource(POSTGRES.getPostgresDatabase())
        .schemas(schema)
        .defaultSchema(schema)
        .baselineVersion("1")
        .baselineOnMigrate(false)
        .cleanDisabled(true)
        .load();
  }

  private Map<String, List<String>> rows(Connection connection, String schema) throws Exception {
    Map<String, List<String>> result = new TreeMap<>();
    for (String table : verifier.inspect(connection, schema).keySet()) {
      List<String> rows = new ArrayList<>();
      try (var statement = connection.createStatement();
          var data =
              statement.executeQuery(
                  "SELECT row_to_json(t)::text FROM " + table + " t ORDER BY id")) {
        while (data.next()) rows.add(data.getString(1));
      }
      result.put(table, rows);
    }
    return result;
  }

  private static void assertNoFlywayHistory(Connection connection, String schema) throws Exception {
    try (var query =
        connection.prepareStatement(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name='flyway_schema_history'")) {
      query.setString(1, schema);
      try (var rows = query.executeQuery()) {
        rows.next();
        assertThat(rows.getInt(1)).isZero();
      }
    }
  }
}
