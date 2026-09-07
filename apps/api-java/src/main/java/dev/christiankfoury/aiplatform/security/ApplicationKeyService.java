package dev.christiankfoury.aiplatform.security;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.persistence.model.*;
import dev.christiankfoury.aiplatform.persistence.repository.AuditLogRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(timeout = 5)
public class ApplicationKeyService {
  public record KeyView(
      UUID id,
      UUID applicationId,
      String keyPrefix,
      String description,
      boolean isActive,
      OffsetDateTime lastUsedAt,
      OffsetDateTime revokedAt,
      OffsetDateTime createdAt) {
    static KeyView from(ApiKey key) {
      return new KeyView(
          key.getId(),
          key.getApplicationId(),
          key.getKeyPrefix(),
          key.getDescription(),
          key.getIsActive(),
          key.getLastUsedAt(),
          key.getRevokedAt(),
          key.getCreatedAt());
    }
  }

  public record CreatedKey(KeyView key, String apiKey) {
    @Override
    public String toString() {
      return "CreatedKey[raw key omitted]";
    }
  }

  private static final SecureRandom RANDOM = new SecureRandom();
  private final EntityManager entities;
  private final OperatorAuthorization authorization;
  private final AuditLogRepository audits;

  public ApplicationKeyService(
      EntityManager entities, OperatorAuthorization authorization, AuditLogRepository audits) {
    this.entities = entities;
    this.authorization = authorization;
    this.audits = audits;
  }

  @Transactional(readOnly = true, timeout = 5)
  public List<KeyView> list(UUID applicationId, int limit) {
    scope(applicationId, false, false);
    return entities
        .createQuery(
            "from ApiKey where applicationId=:app order by createdAt desc, id desc", ApiKey.class)
        .setParameter("app", applicationId)
        .setMaxResults(limit)
        .getResultList()
        .stream()
        .map(KeyView::from)
        .toList();
  }

  public CreatedKey create(UUID applicationId, String description) {
    UUID project = scope(applicationId, true, true);
    byte[] entropy = new byte[32];
    RANDOM.nextBytes(entropy);
    String raw = "pap_" + Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
    ApiKey key = new ApiKey();
    key.setApplicationId(applicationId);
    key.setKeyPrefix(raw.substring(0, 12));
    key.setKeyHash(ApplicationAuthenticator.hash(raw));
    key.setDescription(description);
    entities.persist(key);
    audit(project, key, "api_key.create");
    return new CreatedKey(KeyView.from(key), raw);
  }

  public KeyView revoke(UUID id) {
    UUID app =
        entities
            .createQuery("select applicationId from ApiKey where id=:id", UUID.class)
            .setParameter("id", id)
            .getSingleResultOrNull();
    if (app == null) throw new ApiFailure(404, "Resource not found");
    UUID project = scope(app, true, false);
    // Lock order is project, then key; usage writers insert their project-linked request before
    // touching the key.
    ApiKey key = entities.find(ApiKey.class, id, LockModeType.PESSIMISTIC_WRITE);
    if (key == null) throw new ApiFailure(404, "Resource not found");
    if (Boolean.TRUE.equals(key.getIsActive()) || key.getRevokedAt() == null) {
      key.setIsActive(false);
      if (key.getRevokedAt() == null) key.setRevokedAt(OffsetDateTime.now(ZoneOffset.UTC));
      audit(project, key, "api_key.revoke");
    }
    return KeyView.from(key);
  }

  private UUID scope(UUID app, boolean write, boolean requireActiveApp) {
    UUID projectId =
        entities
            .createQuery("select projectId from ClientApplication where id=:id", UUID.class)
            .setParameter("id", app)
            .getSingleResultOrNull();
    if (projectId == null) throw new ApiFailure(404, "Resource not found");
    authorization.requireResource(projectId, write);
    Project project =
        write
            ? entities.find(Project.class, projectId, LockModeType.PESSIMISTIC_WRITE)
            : entities.find(Project.class, projectId);
    if (project == null || !Boolean.TRUE.equals(project.getIsActive()))
      throw new ApiFailure(404, "Resource not found");
    if (write) authorization.requireResource(projectId, true);
    ClientApplication application = entities.find(ClientApplication.class, app);
    if (application == null
        || (requireActiveApp && !Boolean.TRUE.equals(application.getIsActive())))
      throw new ApiFailure(404, "Resource not found");
    return projectId;
  }

  private void audit(UUID project, ApiKey key, String action) {
    AuditLog audit = new AuditLog();
    audit.setProjectId(project);
    audit.setApplicationId(key.getApplicationId());
    audit.setActorType("operator");
    audit.setActorId(OperatorIdentity.current().actorId());
    audit.setAction(action);
    audit.setResourceType("api_key");
    audit.setResourceId(key.getId().toString());
    audit.setMetadataJson(Map.of("key_prefix", key.getKeyPrefix(), "is_active", key.getIsActive()));
    audits.saveAndFlush(audit);
  }
}
