package dev.christiankfoury.aiplatform.persistence;

import org.flywaydb.core.Flyway;

/**
 * Explicit offline-app migration command. Credentials come from the environment, never CLI args.
 */
public final class MigrationCommand {
  private MigrationCommand() {}

  public static void main(String[] args) {
    if (args.length != 1 || !(args[0].equals("migrate") || args[0].equals("adopt-alembic"))) {
      throw new IllegalArgumentException("Choose migrate or adopt-alembic explicitly");
    }
    String schema = System.getenv().getOrDefault("DATABASE_SCHEMA", "public");
    SchemaContractVerifier.checkSchemaName(schema);
    Flyway flyway =
        Flyway.configure()
            .dataSource(
                required("JDBC_DATABASE_URL"),
                required("DATABASE_USERNAME"),
                required("DATABASE_PASSWORD"))
            .schemas(schema)
            .defaultSchema(schema)
            .baselineVersion("1")
            .baselineOnMigrate(false)
            .cleanDisabled(true)
            .load();
    if (args[0].equals("adopt-alembic")) DatabaseMigrations.adoptAlembic(flyway);
    else DatabaseMigrations.migrate(flyway);
  }

  private static String required(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank())
      throw new IllegalArgumentException("Missing required setting: " + name);
    return value;
  }
}
