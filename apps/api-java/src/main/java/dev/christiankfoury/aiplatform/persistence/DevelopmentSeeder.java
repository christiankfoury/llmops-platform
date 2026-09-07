package dev.christiankfoury.aiplatform.persistence;

import dev.christiankfoury.aiplatform.persistence.model.ApiKey;
import dev.christiankfoury.aiplatform.persistence.model.AuditLog;
import dev.christiankfoury.aiplatform.persistence.model.BaseEntity;
import dev.christiankfoury.aiplatform.persistence.model.ClientApplication;
import dev.christiankfoury.aiplatform.persistence.model.ModelRoute;
import dev.christiankfoury.aiplatform.persistence.model.Project;
import dev.christiankfoury.aiplatform.persistence.model.PromptVersion;
import jakarta.persistence.EntityManager;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Explicit synthetic seed data; existing records and revoked keys are never reactivated. */
@Service
public class DevelopmentSeeder {
  public static final String DEMO_KEY = "local-dev-placeholder-key-not-a-secret";
  public static final String PROOFBASE_KEY = "proofbase-local-placeholder-key-not-a-secret";
  public static final String AGENTOPS_KEY = "agentops-local-placeholder-key-not-a-secret";
  private final EntityManager entityManager;

  public DevelopmentSeeder(EntityManager entityManager) {
    this.entityManager = entityManager;
  }

  @Transactional
  public void seed() {
    seedScope(
        "demo-project",
        "Demo Project",
        "demo-app",
        "Demo App",
        DEMO_KEY,
        "default-chat",
        "You are the local mock provider for the Production AI Platform.",
        "mock",
        "mock-llm-small");
    seedScope(
        "proofbase",
        "Proofbase",
        "enterprise-knowledge-agent",
        "Enterprise Knowledge Agent",
        PROOFBASE_KEY,
        "proofbase-external-telemetry",
        "Placeholder only. Proofbase owns its RAG prompts.",
        "external",
        "reported-by-proofbase");
    seedScope(
        "agentops",
        "AgentOps Workflow Platform",
        "agentops-workflow-platform",
        "AgentOps Workflow Platform",
        AGENTOPS_KEY,
        "agentops-external-telemetry",
        "Placeholder only. AgentOps owns its workflow prompts and outputs.",
        "external",
        "reported-by-agentops");
  }

  private void seedScope(
      String projectSlug,
      String projectName,
      String appSlug,
      String appName,
      String key,
      String promptName,
      String content,
      String provider,
      String model) {
    Project project = first("from Project p where p.slug=?1", Project.class, projectSlug);
    if (project == null) {
      project = new Project();
      initialize(project, "project:" + projectSlug);
      project.setName(projectName);
      project.setSlug(projectSlug);
      project.setDescription("Synthetic local platform client");
      entityManager.persist(project);
    }
    ClientApplication application =
        first(
            "from ClientApplication a where a.projectId=?1 and a.slug=?2",
            ClientApplication.class,
            project.getId(),
            appSlug);
    if (application == null) {
      application = new ClientApplication();
      initialize(application, "app:" + projectSlug + ":" + appSlug);
      application.setProjectId(project.getId());
      application.setName(appName);
      application.setSlug(appSlug);
      entityManager.persist(application);
    }
    String hash = hash(key);
    if (first("from ApiKey k where k.keyHash=?1", ApiKey.class, hash) == null) {
      ApiKey apiKey = new ApiKey();
      initialize(apiKey, "key:" + appSlug);
      apiKey.setApplicationId(application.getId());
      apiKey.setKeyHash(hash);
      apiKey.setKeyPrefix(key.substring(0, Math.min(16, key.length())));
      apiKey.setDescription("Hashed local placeholder, never a production credential");
      entityManager.persist(apiKey);
    }
    if (first(
            "from PromptVersion p where p.projectId=?1 and p.applicationId=?2 and p.name=?3 and p.version=1",
            PromptVersion.class,
            project.getId(),
            application.getId(),
            promptName)
        == null) {
      PromptVersion prompt = new PromptVersion();
      initialize(prompt, "prompt:" + appSlug);
      prompt.setProjectId(project.getId());
      prompt.setApplicationId(application.getId());
      prompt.setName(promptName);
      prompt.setVersion(1);
      prompt.setContent(content);
      entityManager.persist(prompt);
    }
    if (first(
            "from ModelRoute r where r.projectId=?1 and r.applicationId=?2 and r.environment='local' and r.provider=?3 and r.modelName=?4",
            ModelRoute.class,
            project.getId(),
            application.getId(),
            provider,
            model)
        == null) {
      ModelRoute route = new ModelRoute();
      initialize(route, "route:" + appSlug);
      route.setProjectId(project.getId());
      route.setApplicationId(application.getId());
      route.setProvider(provider);
      route.setModelName(model);
      route.setIsDefault(true);
      entityManager.persist(route);
    }
    UUID auditId = identifier("seed-audit:" + appSlug);
    if (entityManager.find(AuditLog.class, auditId) == null) {
      AuditLog audit = new AuditLog();
      initialize(audit, "seed-audit:" + appSlug);
      audit.setProjectId(project.getId());
      audit.setApplicationId(application.getId());
      audit.setActorType("system");
      audit.setActorId("java-local-seed");
      audit.setAction("seed_dev_data");
      audit.setResourceType("database");
      audit.setResourceId("java-phase-51");
      audit.setMetadataJson(Map.of("synthetic", true, "phase", 51));
      entityManager.persist(audit);
    }
  }

  private <T> T first(String hql, Class<T> type, Object... parameters) {
    var query = entityManager.createQuery(hql, type).setMaxResults(1);
    for (int index = 0; index < parameters.length; index++)
      query.setParameter(index + 1, parameters[index]);
    return query.getResultStream().findFirst().orElse(null);
  }

  private static void initialize(BaseEntity entity, String name) {
    entity.setId(identifier(name));
    entity.setCreatedAt(OffsetDateTime.parse("2026-01-01T00:00:00Z"));
    entity.setUpdatedAt(entity.getCreatedAt());
  }

  private static UUID identifier(String name) {
    return UUID.nameUUIDFromBytes(
        ("production-ai-platform:" + name).getBytes(StandardCharsets.UTF_8));
  }

  private static String hash(String key) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(key.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }
}
