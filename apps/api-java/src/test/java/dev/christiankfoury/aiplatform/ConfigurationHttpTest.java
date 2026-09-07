package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.christiankfoury.aiplatform.operator.OperatorPayload;
import dev.christiankfoury.aiplatform.persistence.model.*;
import dev.christiankfoury.aiplatform.persistence.repository.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class ConfigurationHttpTest extends OperatorTestSupport {
  private static final String PROMPTS = "/v1/admin/prompt-versions";
  private static final String ROUTES = "/v1/admin/model-routes";
  @Autowired private PromptVersionRepository prompts;
  @Autowired private ModelRouteRepository routes;
  @MockitoSpyBean private AuditLogRepository audits;

  private Map<String, Object> promptBody() {
    var body = scopeBody();
    body.put("name", "synthetic-chat");
    body.put("content", "Synthetic gateway prompt.");
    return body;
  }

  private Map<String, Object> routeBody() {
    var body = scopeBody();
    body.put("model_name", "mock-llm-small");
    return body;
  }

  private List<PromptVersion> projectPrompts() {
    return prompts.findAll().stream()
        .filter(item -> item.getProjectId().equals(project.getId()))
        .toList();
  }

  private List<ModelRoute> projectRoutes() {
    return routes.findAll().stream()
        .filter(item -> item.getProjectId().equals(project.getId()))
        .toList();
  }

  private List<AuditLog> projectAudits() {
    return audits.findAll().stream()
        .filter(item -> Objects.equals(item.getProjectId(), project.getId()))
        .toList();
  }

  @Test
  void promptCreationUpdateAndRepeatedActivationPreserveContractAndAudit() throws Exception {
    var first =
        response(
            create(PROMPTS, promptBody())
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.version").value(1))
                .andExpect(jsonPath("$.is_active").value(true)));
    assertThat(first.keySet())
        .containsExactlyInAnyOrder(
            "id", "project_id", "application_id", "name", "version", "content", "is_active");
    var second =
        response(
            create(PROMPTS, promptBody())
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.version").value(2)));
    UUID firstId = UUID.fromString(first.get("id").toString());
    assertThat(prompts.findById(firstId).orElseThrow().getIsActive()).isFalse();
    for (int i = 0; i < 2; i++)
      http.perform(post(PROMPTS + "/" + firstId + "/activate"))
          .andExpect(status().isOk())
          .andExpect(jsonPath("$.is_active").value(true));
    assertThat(prompts.findById(firstId).orElseThrow().getIsActive()).isTrue();
    assertThat(
            prompts
                .findById(UUID.fromString(second.get("id").toString()))
                .orElseThrow()
                .getIsActive())
        .isFalse();
    http.perform(
            patch(PROMPTS + "/" + firstId)
                .contentType("application/json")
                .content("{\"content\":\"Updated synthetic prompt.\",\"is_active\":null}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").value("Updated synthetic prompt."));
    assertThat(projectAudits())
        .hasSize(5)
        .allSatisfy(
            audit -> {
              assertThat(audit.getActorId())
                  .isEqualTo(
                      new dev.christiankfoury.aiplatform.security.OperatorIdentity(
                              OPERATOR_ISSUER, OPERATOR_SUBJECT)
                          .actorId());
              assertThat(audit.getActorType()).isEqualTo("operator");
              assertThat(audit.getApplicationId()).isEqualTo(application.getId());
              assertThat(audit.getMetadataJson().toString())
                  .doesNotContain("Updated synthetic prompt.", "Synthetic gateway prompt.");
            });
    http.perform(get(PROMPTS).param("limit", "1"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(1));
  }

  @Test
  void parallelPromptCreationAllocatesDistinctVersionsAndOneActiveVersion() throws Exception {
    CyclicBarrier barrier = new CyclicBarrier(4);
    try (var executor = Executors.newFixedThreadPool(4)) {
      List<Future<Map<String, Object>>> submitted = new ArrayList<>();
      for (int i = 0; i < 4; i++)
        submitted.add(
            executor.submit(
                () -> {
                  barrier.await(5, TimeUnit.SECONDS);
                  return response(create(PROMPTS, promptBody()).andExpect(status().isCreated()));
                }));
      Set<Object> versions = new HashSet<>();
      for (var result : submitted) versions.add(result.get(15, TimeUnit.SECONDS).get("version"));
      assertThat(versions).containsExactlyInAnyOrder(1, 2, 3, 4);
    }
    assertThat(projectPrompts()).hasSize(4);
    assertThat(projectPrompts().stream().filter(PromptVersion::getIsActive)).hasSize(1);
    assertThat(projectAudits()).hasSize(4);
  }

  @Test
  void activationDoesNotChangeAnotherApplicationOrPromptName() throws Exception {
    var original = response(create(PROMPTS, promptBody()).andExpect(status().isCreated()));
    var named = promptBody();
    named.put("name", "other-name");
    var otherName = response(create(PROMPTS, named).andExpect(status().isCreated()));
    transaction()
        .executeWithoutResult(
            status -> {
              var another = new ClientApplication();
              another.setProjectId(project.getId());
              another.setName("Other synthetic app");
              another.setSlug("other-client");
              entities.persist(another);
            });
    var other = promptBody();
    other.put("application_slug", "other-client");
    var otherApp = response(create(PROMPTS, other).andExpect(status().isCreated()));
    create(PROMPTS, promptBody()).andExpect(status().isCreated());
    http.perform(post(PROMPTS + "/" + original.get("id") + "/activate")).andExpect(status().isOk());
    for (var id : List.of(original.get("id"), otherName.get("id"), otherApp.get("id")))
      assertThat(prompts.findById(UUID.fromString(id.toString())).orElseThrow().getIsActive())
          .isTrue();
    assertThat(projectPrompts().stream().filter(PromptVersion::getIsActive)).hasSize(3);
  }

  @Test
  void gatewayUsesThePromptAndRouteCreatedThroughOperatorApis() throws Exception {
    String key = "operator-gateway-placeholder-" + UUID.randomUUID();
    transaction()
        .executeWithoutResult(
            status -> {
              ApiKey apiKey = new ApiKey();
              apiKey.setApplicationId(application.getId());
              apiKey.setKeyPrefix("operator-test");
              apiKey.setKeyHash(
                  dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator.hash(key));
              entities.persist(apiKey);
            });
    create(PROMPTS, promptBody()).andExpect(status().isCreated());
    create(ROUTES, routeBody()).andExpect(status().isCreated());
    http.perform(
            post("/v1/gateway/completions")
                .header("X-API-Key", key)
                .contentType("application/json")
                .content("{\"input\":\"synthetic hello\",\"prompt_name\":\"synthetic-chat\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("succeeded"))
        .andExpect(jsonPath("$.model").value("mock-llm-small"))
        .andExpect(
            jsonPath("$.output")
                .value(
                    "[mock:mock-llm-small] Synthetic gateway prompt. Input received: synthetic hello"));
  }

  @Test
  void explicitVersionConflictDoesNotDeactivateExistingConfiguration() throws Exception {
    var body = promptBody();
    body.put("version", 7);
    create(PROMPTS, body).andExpect(status().isCreated()).andExpect(jsonPath("$.version").value(7));
    create(PROMPTS, body)
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.detail").value("Prompt version already exists"));
    assertThat(projectPrompts())
        .hasSize(1)
        .allSatisfy(prompt -> assertThat(prompt.getIsActive()).isTrue());
    assertThat(projectAudits()).hasSize(1);
  }

  @Test
  void routesKeepOneDefaultPerEnvironmentAndRepeatedActivationWorks() throws Exception {
    var first = response(create(ROUTES, routeBody()).andExpect(status().isCreated()));
    assertThat(first.keySet())
        .containsExactlyInAnyOrder(
            "id",
            "project_id",
            "application_id",
            "environment",
            "provider",
            "model_name",
            "priority",
            "is_default",
            "is_active");
    assertThat(first)
        .containsEntry("environment", "local")
        .containsEntry("provider", "mock")
        .containsEntry("priority", 100);
    var secondBody = routeBody();
    secondBody.put("is_active", false);
    var second = response(create(ROUTES, secondBody).andExpect(status().isCreated()));
    var staging = routeBody();
    staging.put("environment", "staging");
    create(ROUTES, staging).andExpect(status().isCreated());
    UUID firstId = UUID.fromString(first.get("id").toString()),
        secondId = UUID.fromString(second.get("id").toString());
    assertThat(routes.findById(firstId).orElseThrow().getIsDefault()).isFalse();
    for (int i = 0; i < 2; i++)
      http.perform(post(ROUTES + "/" + secondId + "/activate"))
          .andExpect(status().isOk())
          .andExpect(jsonPath("$.is_default").value(true))
          .andExpect(jsonPath("$.is_active").value(true));
    http.perform(
            patch(ROUTES + "/" + firstId)
                .contentType("application/json")
                .content("{\"priority\":1,\"is_default\":true}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.priority").value(1));
    assertThat(routes.findById(secondId).orElseThrow().getIsDefault()).isFalse();
    assertThat(projectRoutes().stream().filter(ModelRoute::getIsDefault)).hasSize(2);
    assertThat(projectAudits()).hasSize(6);
  }

  @Test
  void simultaneousRouteCreationLeavesOneDefault() throws Exception {
    CyclicBarrier barrier = new CyclicBarrier(4);
    try (var executor = Executors.newFixedThreadPool(4)) {
      List<Future<?>> submitted = new ArrayList<>();
      for (int i = 0; i < 4; i++)
        submitted.add(
            executor.submit(
                () -> {
                  barrier.await(5, TimeUnit.SECONDS);
                  create(ROUTES, routeBody()).andExpect(status().isCreated());
                  return null;
                }));
      for (var result : submitted) result.get(15, TimeUnit.SECONDS);
    }
    assertThat(projectRoutes()).hasSize(4);
    assertThat(projectRoutes().stream().filter(ModelRoute::getIsDefault)).hasSize(1);
  }

  @Test
  void auditFailureRollsBackNewVersionAndPriorDeactivation(CapturedOutput output) throws Exception {
    create(PROMPTS, promptBody()).andExpect(status().isCreated());
    doThrow(new IllegalStateException("synthetic-diagnostic-must-not-leak"))
        .when(audits)
        .saveAndFlush(any());
    create(PROMPTS, promptBody())
        .andExpect(status().isInternalServerError())
        .andExpect(jsonPath("$.detail").value("Internal server error"));
    assertThat(projectPrompts())
        .hasSize(1)
        .allSatisfy(prompt -> assertThat(prompt.getIsActive()).isTrue());
    assertThat(projectAudits()).hasSize(1);
    assertThat(output.getAll())
        .doesNotContain("synthetic-diagnostic-must-not-leak", "Synthetic gateway prompt.");
  }

  @Test
  void invalidPayloadsAreRejectedBeforeConfigurationChanges() throws Exception {
    for (var change :
        List.of(
            Map.<String, Object>of("version", 1.5),
            Map.<String, Object>of("version", "1"),
            Map.<String, Object>of("is_active", "true"),
            Map.<String, Object>of("content", "x".repeat(32001)),
            Map.<String, Object>of("unknown", "synthetic-private"))) {
      var body = promptBody();
      body.putAll(change);
      create(PROMPTS, body).andExpect(status().is(422));
    }
    http.perform(
            post(PROMPTS)
                .contentType("application/json")
                .content("{\"name\":\"a\",\"name\":\"b\"}"))
        .andExpect(status().is(422));
    http.perform(
            post(PROMPTS)
                .contentType("application/json")
                .content(" ".repeat(OperatorPayload.MAX_BYTES + 1)))
        .andExpect(status().is(413));
    var body = routeBody();
    body.put("priority", null);
    create(ROUTES, body).andExpect(status().is(422));
    assertThat(projectPrompts()).isEmpty();
    assertThat(projectRoutes()).isEmpty();
    assertThat(projectAudits()).isEmpty();
  }

  @Test
  void inactiveAndMissingScopesAndResourcesAreRefused() throws Exception {
    var body = promptBody();
    body.put("application_slug", "missing-app");
    create(PROMPTS, body).andExpect(status().isNotFound());
    http.perform(post(PROMPTS + "/" + UUID.randomUUID() + "/activate"))
        .andExpect(status().isNotFound());
    http.perform(post(ROUTES + "/" + UUID.randomUUID() + "/activate"))
        .andExpect(status().isNotFound());
    transaction()
        .executeWithoutResult(
            status ->
                entities.find(ClientApplication.class, application.getId()).setIsActive(false));
    create(PROMPTS, promptBody()).andExpect(status().isNotFound());
    transaction()
        .executeWithoutResult(
            status -> {
              entities.find(ClientApplication.class, application.getId()).setIsActive(true);
              entities.find(Project.class, project.getId()).setIsActive(false);
            });
    create(ROUTES, routeBody()).andExpect(status().isNotFound());
  }

  @Test
  void machineHeadersCannotAuthorizeOperatorActivation() throws Exception {
    var created = response(create(PROMPTS, promptBody()).andExpect(status().isCreated()));
    http.perform(
            post(PROMPTS + "/" + created.get("id") + "/activate")
                .with(
                    org.springframework.security.test.web.servlet.request
                        .SecurityMockMvcRequestPostProcessors.anonymous())
                .header("X-API-Key", "synthetic-machine-key")
                .header("X-Actor-ID", "spoofed-operator"))
        .andExpect(status().isUnauthorized());
    assertThat(projectAudits()).hasSize(1);
  }
}
