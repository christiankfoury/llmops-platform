package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;

import dev.christiankfoury.aiplatform.persistence.DatabaseTransport;
import dev.christiankfoury.aiplatform.persistence.LocalSeedBoundary;
import java.util.List;
import org.junit.jupiter.api.Test;

class DatabaseTransportTest {
  @Test
  void hostedDatabaseRequiresHostnameVerificationAndCannotOverrideIt() {
    String prefix = "jdbc:postgresql://database.example.invalid:5432/platform?";
    DatabaseTransport.require(
        prefix + "sslmode=verify-full&sslrootcert=/certificates/root.crt", "prod");
    for (String query :
        List.of(
            "",
            "sslmode=require",
            "sslmode=verify-ca",
            "sslmode=disable",
            "sslmode=verify-full&sslmode=disable",
            "sslmode=verify-full&sslfactory=org.postgresql.ssl.NonValidatingFactory",
            "sslmode=verify-full&sslhostnameverifier=unsafe",
            "sslmode=verify-full&password=synthetic-secret",
            "sslmode=verify-full&user=owner"))
      assertThatThrownBy(() -> DatabaseTransport.require(prefix + query, "prod"))
          .isInstanceOf(IllegalArgumentException.class)
          .hasMessage(
              "Hosted PostgreSQL requires verify-full TLS, verified trust and separate credentials");
    DatabaseTransport.require("jdbc:postgresql://localhost/platform", "local");
  }

  @Test
  void composeSeedingIsExplicitLocalAndRestrictedToItsService() {
    LocalSeedBoundary.require("local", "jdbc:postgresql://localhost:5432/platform", false);
    LocalSeedBoundary.require("local", "jdbc:postgresql://postgres:5432/platform", true);
    assertThatThrownBy(
            () ->
                LocalSeedBoundary.require(
                    "local", "jdbc:postgresql://postgres:5432/platform", false))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () ->
                LocalSeedBoundary.require("prod", "jdbc:postgresql://postgres:5432/platform", true))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () ->
                LocalSeedBoundary.require(
                    "local", "jdbc:postgresql://remote.example.invalid/platform", true))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
