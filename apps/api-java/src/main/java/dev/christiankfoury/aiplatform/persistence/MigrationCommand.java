package dev.christiankfoury.aiplatform.persistence;

import org.flywaydb.core.Flyway;

/**
 * Explicit offline-app migration command. Credentials come from the environment, never CLI args.
 */
public final class MigrationCommand {
  private MigrationCommand() {}

  public static void main(String[] args) throws java.sql.SQLException {
    if (args.length != 1
        || !java.util.Set.of(
                "migrate", "adopt-alembic", "grant-operator", "revoke-operator-grant", "seed-local")
            .contains(args[0])) {
      throw new IllegalArgumentException(
          "Choose migrate, adopt-alembic, grant-operator, revoke-operator-grant, or seed-local explicitly");
    }
    String url = required("JDBC_DATABASE_URL");
    String environment = System.getenv().getOrDefault("ENVIRONMENT", "local");
    DatabaseTransport.require(url, environment);
    if (args[0].equals("seed-local")) {
      LocalSeedBoundary.require(
          environment,
          url,
          Boolean.parseBoolean(
              System.getenv().getOrDefault("SEED_ALLOW_COMPOSE_NETWORK", "false")));
      var application =
          new org.springframework.boot.SpringApplication(
              dev.christiankfoury.aiplatform.PlatformApplication.class);
      application.setWebApplicationType(org.springframework.boot.WebApplicationType.NONE);
      var context =
          application.run("--platform.seed.enabled=true", "--spring.flyway.enabled=false");
      context.close();
      return;
    }
    String schema = System.getenv().getOrDefault("DATABASE_SCHEMA", "public");
    SchemaContractVerifier.checkSchemaName(schema);
    if (args[0].equals("grant-operator") || args[0].equals("revoke-operator-grant")) {
      try (var connection =
          java.sql.DriverManager.getConnection(
              required("JDBC_DATABASE_URL"),
              required("DATABASE_USERNAME"),
              required("DATABASE_PASSWORD"))) {
        dev.christiankfoury.aiplatform.security.OperatorGrantCommand.execute(
            connection,
            schema,
            required("OIDC_ISSUER"),
            required("OPERATOR_SUBJECT"),
            required("OPERATOR_PROJECT_SLUG"),
            required("OPERATOR_ROLE"),
            args[0].equals("revoke-operator-grant"));
      }
      return;
    }
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
