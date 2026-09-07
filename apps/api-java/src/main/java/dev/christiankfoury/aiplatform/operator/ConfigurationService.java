package dev.christiankfoury.aiplatform.operator;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.persistence.model.*;
import dev.christiankfoury.aiplatform.persistence.repository.AuditLogRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(timeout = 5)
public class ConfigurationService {
  private final EntityManager entities;
  private final AuditLogRepository audits;

  public ConfigurationService(EntityManager entities, AuditLogRepository audits) {
    this.entities = entities;
    this.audits = audits;
  }

  @Transactional(readOnly = true, timeout = 5)
  public List<ConfigurationViews.Prompt> prompts(int limit) {
    return entities
        .createQuery("from PromptVersion order by createdAt desc, id desc", PromptVersion.class)
        .setMaxResults(limit)
        .getResultList()
        .stream()
        .map(ConfigurationViews.Prompt::from)
        .toList();
  }

  @Transactional(readOnly = true, timeout = 5)
  public List<ConfigurationViews.Route> routes(int limit) {
    return entities
        .createQuery("from ModelRoute order by createdAt desc, id desc", ModelRoute.class)
        .setMaxResults(limit)
        .getResultList()
        .stream()
        .map(ConfigurationViews.Route::from)
        .toList();
  }

  public ConfigurationViews.Prompt createPrompt(OperatorPayload payload) {
    ClientApplication application =
        scope(payload.text("project_slug"), payload.text("application_slug"));
    UUID project = application.getProjectId(), app = application.getId();
    String name = payload.text("name");
    Integer version = payload.integer("version");
    if (version == null) {
      int current =
          entities
              .createQuery(
                  "select coalesce(max(version), 0) from PromptVersion where projectId=:project and applicationId=:app and name=:name",
                  Integer.class)
              .setParameter("project", project)
              .setParameter("app", app)
              .setParameter("name", name)
              .getSingleResult();
      if (current == Integer.MAX_VALUE) throw new ApiFailure(409, "Prompt version range exhausted");
      version = current + 1;
    }
    if (entities
            .createQuery(
                "select count(*) from PromptVersion where projectId=:project and applicationId=:app and name=:name and version=:version",
                Long.class)
            .setParameter("project", project)
            .setParameter("app", app)
            .setParameter("name", name)
            .setParameter("version", version)
            .getSingleResult()
        > 0) throw new ApiFailure(409, "Prompt version already exists");
    boolean active = payload.flag("is_active", true);
    if (active) deactivatePrompts(project, app, name);
    PromptVersion prompt = new PromptVersion();
    prompt.setProjectId(project);
    prompt.setApplicationId(app);
    prompt.setName(name);
    prompt.setVersion(version);
    prompt.setContent(payload.text("content"));
    prompt.setIsActive(active);
    entities.persist(prompt);
    audit(
        prompt,
        "prompt_version.create",
        "prompt_version",
        Map.of("name", name, "version", version, "is_active", active));
    return ConfigurationViews.Prompt.from(prompt);
  }

  public ConfigurationViews.Prompt updatePrompt(UUID id, OperatorPayload payload) {
    return changePrompt(id, payload, false);
  }

  public ConfigurationViews.Prompt activatePrompt(UUID id) {
    return changePrompt(id, null, true);
  }

  private ConfigurationViews.Prompt changePrompt(
      UUID id, OperatorPayload payload, boolean activate) {
    UUID projectId =
        entities
            .createQuery("select projectId from PromptVersion where id=:id", UUID.class)
            .setParameter("id", id)
            .getSingleResultOrNull();
    if (projectId == null) throw new ApiFailure(404, "Prompt version not found");
    lockProject(projectId);
    PromptVersion prompt = entities.find(PromptVersion.class, id);
    if (prompt == null) throw new ApiFailure(404, "Prompt version not found");
    activeApplication(projectId, prompt.getApplicationId());
    Boolean active = activate ? Boolean.TRUE : payload.flag("is_active");
    if (Boolean.TRUE.equals(active)) {
      deactivatePrompts(projectId, prompt.getApplicationId(), prompt.getName());
      entities.refresh(
          prompt); // Bulk deactivation must not leave stale true flags in the persistence context.
    }
    if (payload != null && payload.text("content") != null)
      prompt.setContent(payload.text("content"));
    if (active != null) prompt.setIsActive(active);
    audit(
        prompt,
        "prompt_version.update",
        "prompt_version",
        Map.of("is_active", prompt.getIsActive()));
    return ConfigurationViews.Prompt.from(prompt);
  }

  public ConfigurationViews.Route createRoute(OperatorPayload payload) {
    ClientApplication application =
        scope(payload.text("project_slug"), payload.text("application_slug"));
    boolean isDefault = payload.flag("is_default", true);
    String environment = payload.text("environment", "local");
    if (isDefault) clearDefaults(application.getProjectId(), application.getId(), environment);
    ModelRoute route = new ModelRoute();
    route.setProjectId(application.getProjectId());
    route.setApplicationId(application.getId());
    route.setEnvironment(environment);
    route.setProvider(payload.text("provider", "mock"));
    route.setModelName(payload.text("model_name"));
    route.setPriority(payload.integer("priority", 100));
    route.setIsDefault(isDefault);
    route.setIsActive(payload.flag("is_active", true));
    entities.persist(route);
    audit(route, "model_route.create", "model_route", routeMetadata(route));
    return ConfigurationViews.Route.from(route);
  }

  public ConfigurationViews.Route updateRoute(UUID id, OperatorPayload payload) {
    return changeRoute(id, payload, false);
  }

  public ConfigurationViews.Route activateRoute(UUID id) {
    return changeRoute(id, null, true);
  }

  private ConfigurationViews.Route changeRoute(UUID id, OperatorPayload payload, boolean activate) {
    UUID projectId =
        entities
            .createQuery("select projectId from ModelRoute where id=:id", UUID.class)
            .setParameter("id", id)
            .getSingleResultOrNull();
    if (projectId == null) throw new ApiFailure(404, "Model route not found");
    lockProject(projectId);
    ModelRoute route = entities.find(ModelRoute.class, id);
    if (route == null) throw new ApiFailure(404, "Model route not found");
    activeApplication(projectId, route.getApplicationId());
    Boolean isDefault = activate ? Boolean.TRUE : payload.flag("is_default");
    if (Boolean.TRUE.equals(isDefault)) {
      clearDefaults(projectId, route.getApplicationId(), route.getEnvironment());
      entities.refresh(route);
    }
    if (payload != null) {
      if (payload.text("provider") != null) route.setProvider(payload.text("provider"));
      if (payload.text("model_name") != null) route.setModelName(payload.text("model_name"));
      if (payload.integer("priority") != null) route.setPriority(payload.integer("priority"));
      if (payload.flag("is_active") != null) route.setIsActive(payload.flag("is_active"));
    }
    if (isDefault != null) route.setIsDefault(isDefault);
    if (activate) route.setIsActive(true);
    audit(route, "model_route.update", "model_route", routeMetadata(route));
    return ConfigurationViews.Route.from(route);
  }

  private ClientApplication scope(String projectSlug, String applicationSlug) {
    UUID projectId =
        entities
            .createQuery("select id from Project where slug=:slug", UUID.class)
            .setParameter("slug", projectSlug)
            .getSingleResultOrNull();
    if (projectId == null) throw new ApiFailure(404, "Project not found");
    lockProject(projectId);
    ClientApplication application =
        entities
            .createQuery(
                "from ClientApplication where projectId=:project and slug=:slug and isActive=true",
                ClientApplication.class)
            .setParameter("project", projectId)
            .setParameter("slug", applicationSlug)
            .getSingleResultOrNull();
    if (application == null) throw new ApiFailure(404, "Application not found");
    return application;
  }

  private void lockProject(UUID id) {
    // A shared parent lock also serializes the initially empty prompt/default-route scopes.
    Project project = entities.find(Project.class, id, LockModeType.PESSIMISTIC_WRITE);
    if (project == null || !Boolean.TRUE.equals(project.getIsActive()))
      throw new ApiFailure(404, "Project not found");
  }

  private void activeApplication(UUID project, UUID id) {
    if (id == null) return; // Preserve historical project-wide configuration rows.
    ClientApplication application = entities.find(ClientApplication.class, id);
    if (application == null
        || !application.getProjectId().equals(project)
        || !Boolean.TRUE.equals(application.getIsActive()))
      throw new ApiFailure(404, "Application not found");
  }

  private void deactivatePrompts(UUID project, UUID app, String name) {
    entities
        .createQuery(
            "update PromptVersion set isActive=false, updatedAt=:now where projectId=:project and applicationId is not distinct from :app and name=:name and isActive=true")
        .setParameter("project", project)
        .setParameter("app", app)
        .setParameter("name", name)
        .setParameter("now", OffsetDateTime.now(ZoneOffset.UTC))
        .executeUpdate();
  }

  private void clearDefaults(UUID project, UUID app, String environment) {
    entities
        .createQuery(
            "update ModelRoute set isDefault=false, updatedAt=:now where projectId=:project and applicationId is not distinct from :app and environment=:environment and isDefault=true")
        .setParameter("project", project)
        .setParameter("app", app)
        .setParameter("environment", environment)
        .setParameter("now", OffsetDateTime.now(ZoneOffset.UTC))
        .executeUpdate();
  }

  private static Map<String, Object> routeMetadata(ModelRoute route) {
    return Map.of(
        "environment",
        route.getEnvironment(),
        "provider",
        route.getProvider(),
        "model_name",
        route.getModelName(),
        "is_default",
        route.getIsDefault(),
        "is_active",
        route.getIsActive());
  }

  private void audit(
      BaseEntity resource, String action, String type, Map<String, Object> metadata) {
    AuditLog audit = new AuditLog();
    if (resource instanceof PromptVersion prompt) {
      audit.setProjectId(prompt.getProjectId());
      audit.setApplicationId(prompt.getApplicationId());
    } else if (resource instanceof ModelRoute route) {
      audit.setProjectId(route.getProjectId());
      audit.setApplicationId(route.getApplicationId());
    }
    audit.setActorType("admin");
    audit.setActorId("local-admin");
    audit.setAction(action);
    audit.setResourceType(type);
    audit.setResourceId(resource.getId().toString());
    audit.setMetadataJson(metadata);
    audits.saveAndFlush(audit);
  }
}
