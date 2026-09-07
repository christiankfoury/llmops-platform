package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.persistence.model.*;
import dev.christiankfoury.aiplatform.security.OperatorGrantCommand;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class OperatorAuthorizationHttpTest extends OperatorTestSupport {
  @Autowired javax.sql.DataSource database;

  String keysPath() {
    return "/v1/admin/applications/" + application.getId() + "/api-keys";
  }

  void role(String role, boolean active) {
    transaction()
        .executeWithoutResult(
            s ->
                entities
                    .createQuery(
                        "update OperatorProjectGrant set role=:role, isActive=:active where projectId=:project")
                    .setParameter("role", role)
                    .setParameter("active", active)
                    .setParameter("project", project.getId())
                    .executeUpdate());
  }

  @Test
  void viewerCanReadButCannotCreateKeysOrChangeConfiguration() throws Exception {
    role("viewer", true);
    http.perform(get(keysPath())).andExpect(status().isOk());
    create(keysPath(), Map.of()).andExpect(status().isNotFound());
    var payload = scopeBody();
    payload.put("name", "forbidden");
    payload.put("content", "forbidden");
    create("/v1/admin/prompt-versions", payload).andExpect(status().isNotFound());
  }

  @Test
  void anotherIdentityCannotReadOrWriteProjectResourcesDespiteRoleClaims() throws Exception {
    var impostor = jwt().jwt(operatorJwt("ungranted-identity")).authorities(() -> "ROLE_OPERATOR");
    http.perform(get(keysPath()).with(impostor)).andExpect(status().isNotFound());
    http.perform(
            get("/v1/usage/summary").param("project_id", project.getId().toString()).with(impostor))
        .andExpect(status().isForbidden());
    http.perform(get("/v1/usage/scopes").with(impostor)).andExpect(content().json("[]"));
    http.perform(post(keysPath()).with(impostor).contentType("application/json").content("{}"))
        .andExpect(status().isNotFound());
  }

  @Test
  void keyIsReturnedOnceStoredAsHashAndRevocationIsIdempotent() throws Exception {
    var created =
        response(
            create(keysPath(), Map.of("description", "synthetic integration key"))
                .andExpect(status().isCreated()));
    String raw = (String) created.get("api_key");
    assertThat(raw).matches("pap_[A-Za-z0-9_-]{43}");
    @SuppressWarnings("unchecked")
    var view = (Map<String, Object>) created.get("key");
    UUID id = UUID.fromString((String) view.get("id"));
    var key = transaction().execute(s -> entities.find(ApiKey.class, id));
    assertThat(key.getKeyHash()).isEqualTo(ApplicationAuthenticator.hash(raw));
    assertThat(key.getLastUsedAt()).isNull();
    var listing =
        http.perform(get(keysPath()))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(listing).doesNotContain(raw, key.getKeyHash(), "key_hash");
    http.perform(
            get("/v1/operator/me")
                .with(
                    org.springframework.security.test.web.servlet.request
                        .SecurityMockMvcRequestPostProcessors.anonymous())
                .header("X-API-Key", raw))
        .andExpect(status().isUnauthorized());
    create("/v1/admin/api-keys/" + id + "/revoke", Map.of())
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.is_active").value(false));
    create("/v1/admin/api-keys/" + id + "/revoke", Map.of()).andExpect(status().isOk());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", raw)
                .contentType("application/json")
                .content("{\"input\":\"synthetic\"}"))
        .andExpect(status().isUnauthorized());
    transaction()
        .executeWithoutResult(
            s -> {
              var audits =
                  entities
                      .createQuery(
                          "from AuditLog where resourceId=:id order by createdAt", AuditLog.class)
                      .setParameter("id", id.toString())
                      .getResultList();
              assertThat(audits).hasSize(2);
              assertThat(audits)
                  .allSatisfy(
                      a -> {
                        assertThat(a.getActorType()).isEqualTo("operator");
                        assertThat(a.getActorId()).startsWith("oidc:");
                        assertThat(a.getMetadataJson().toString())
                            .doesNotContain(raw, key.getKeyHash());
                      });
            });
  }

  @Test
  void lastUsedIsRecordedWithGatewayTransactionWithoutReactivatingRevokedKeys() throws Exception {
    var created = response(create(keysPath(), Map.of()).andExpect(status().isCreated()));
    String raw = (String) created.get("api_key");
    @SuppressWarnings("unchecked")
    UUID id = UUID.fromString((String) ((Map<String, Object>) created.get("key")).get("id"));
    var prompt = scopeBody();
    prompt.put("name", "default-chat");
    prompt.put("content", "Synthetic prompt");
    create("/v1/admin/prompt-versions", prompt).andExpect(status().isCreated());
    var route = scopeBody();
    route.put("environment", "local");
    route.put("provider", "mock");
    route.put("model_name", "mock-llm-small");
    route.put("is_default", true);
    create("/v1/admin/model-routes", route).andExpect(status().isCreated());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", raw)
                .contentType("application/json")
                .content("{\"input\":\"synthetic\"}"))
        .andExpect(status().isOk());
    assertThat(
            transaction()
                .<java.time.OffsetDateTime>execute(
                    s -> entities.find(ApiKey.class, id).getLastUsedAt()))
        .isNotNull();
    create("/v1/admin/api-keys/" + id + "/revoke", Map.of()).andExpect(status().isOk());
    assertThat(transaction().<Boolean>execute(s -> entities.find(ApiKey.class, id).getIsActive()))
        .isFalse();
  }

  @Test
  void databaseOwnerProvisioningAndRevocationTakeEffectOnNextRequest() throws Exception {
    try (var connection = database.getConnection()) {
      OperatorGrantCommand.execute(
          connection,
          "operator_test",
          OPERATOR_ISSUER,
          OPERATOR_SUBJECT,
          project.getSlug(),
          "viewer",
          false);
    }
    http.perform(get(keysPath())).andExpect(status().isOk());
    create(keysPath(), Map.of()).andExpect(status().isNotFound());
    try (var connection = database.getConnection()) {
      OperatorGrantCommand.execute(
          connection,
          "operator_test",
          OPERATOR_ISSUER,
          OPERATOR_SUBJECT,
          project.getSlug(),
          "viewer",
          true);
    }
    http.perform(get(keysPath())).andExpect(status().isNotFound());
    http.perform(get("/v1/usage/summary").param("project_id", project.getId().toString()))
        .andExpect(status().isForbidden());
  }

  @Test
  void inactiveProjectImmediatelyLosesReadAndWriteAccess() throws Exception {
    transaction()
        .executeWithoutResult(
            s -> entities.find(Project.class, project.getId()).setIsActive(false));
    http.perform(get(keysPath())).andExpect(status().isNotFound());
    create(keysPath(), Map.of()).andExpect(status().isNotFound());
  }

  @Test
  void keyAndGrantWritesRollbackWhenTheirAuditCannotCommit() throws Exception {
    try (var connection = database.getConnection();
        var statement = connection.createStatement()) {
      statement.execute(
          "ALTER TABLE operator_test.audit_logs ADD CONSTRAINT fixture_reject_auth_audit CHECK (action NOT IN ('api_key.create', 'operator_grant.upsert')) NOT VALID");
    }
    try {
      create(keysPath(), Map.of()).andExpect(status().isInternalServerError());
      assertThat(
              transaction()
                  .<Long>execute(
                      s ->
                          entities
                              .createQuery(
                                  "select count(k) from ApiKey k where applicationId=:app",
                                  Long.class)
                              .setParameter("app", application.getId())
                              .getSingleResult()))
          .isZero();
      try (var connection = database.getConnection()) {
        assertThatThrownBy(
                () ->
                    OperatorGrantCommand.execute(
                        connection,
                        "operator_test",
                        OPERATOR_ISSUER,
                        OPERATOR_SUBJECT,
                        project.getSlug(),
                        "viewer",
                        false))
            .isInstanceOf(java.sql.SQLException.class);
      }
      // Failed downgrade did not change the existing operator grant.
      assertThat(
              transaction()
                  .<String>execute(
                      s ->
                          entities
                              .createQuery(
                                  "select role from OperatorProjectGrant where projectId=:project",
                                  String.class)
                              .setParameter("project", project.getId())
                              .getSingleResult()))
          .isEqualTo("operator");
    } finally {
      try (var connection = database.getConnection();
          var statement = connection.createStatement()) {
        statement.execute(
            "ALTER TABLE operator_test.audit_logs DROP CONSTRAINT fixture_reject_auth_audit");
      }
    }
  }
}
