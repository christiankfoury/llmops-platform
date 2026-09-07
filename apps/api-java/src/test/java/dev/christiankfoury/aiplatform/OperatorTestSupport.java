package dev.christiankfoury.aiplatform;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

import dev.christiankfoury.aiplatform.persistence.model.ClientApplication;
import dev.christiankfoury.aiplatform.persistence.model.Project;
import jakarta.persistence.EntityManager;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

abstract class OperatorTestSupport extends PostgresTestSupport {
  @Autowired protected MockMvc http;
  @Autowired protected JsonMapper json;
  @Autowired protected EntityManager entities;
  @Autowired protected PlatformTransactionManager transactionManager;
  protected Project project;
  protected ClientApplication application;

  @DynamicPropertySource
  static void operatorSchema(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.hikari.schema", () -> "operator_test");
    registry.add("spring.jpa.properties.hibernate.default_schema", () -> "operator_test");
    registry.add("spring.flyway.default-schema", () -> "operator_test");
    registry.add("spring.flyway.schemas", () -> "operator_test");
  }

  @BeforeEach
  void operatorFixture() {
    transaction()
        .executeWithoutResult(
            status -> {
              project = new Project();
              project.setName("Synthetic operator project");
              project.setSlug("operator_" + UUID.randomUUID());
              entities.persist(project);
              application = new ClientApplication();
              application.setProjectId(project.getId());
              application.setName("Synthetic operator app");
              application.setSlug("synthetic-client");
              entities.persist(application);
            });
  }

  protected TransactionTemplate transaction() {
    return new TransactionTemplate(transactionManager);
  }

  protected Map<String, Object> scopeBody() {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("project_slug", project.getSlug());
    body.put("application_slug", application.getSlug());
    return body;
  }

  protected ResultActions create(String path, Map<String, Object> body) throws Exception {
    return http.perform(
        post(path)
            .header("Host", "localhost:8080")
            .header("X-Actor-ID", "spoofed-actor-must-be-ignored")
            .contentType("application/json")
            .content(json.writeValueAsString(body)));
  }

  protected Map<String, Object> response(ResultActions result) throws Exception {
    return json.readValue(
        result.andReturn().getResponse().getContentAsString(), new TypeReference<>() {});
  }
}
