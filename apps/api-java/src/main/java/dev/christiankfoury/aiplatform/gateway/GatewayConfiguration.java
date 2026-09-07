package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.persistence.model.ModelRoute;
import dev.christiankfoury.aiplatform.persistence.model.PromptVersion;
import jakarta.persistence.EntityManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GatewayConfiguration {
  private final ApplicationAuthenticator authenticator;
  private final EntityManager entities;

  public GatewayConfiguration(ApplicationAuthenticator authenticator, EntityManager entities) {
    this.authenticator = authenticator;
    this.entities = entities;
  }

  @Transactional(readOnly = true)
  public GatewayContext resolve(String key, CompletionRequest request) {
    var scope = authenticator.authenticate(key);
    var prompt =
        entities
            .createQuery(
                """
        from PromptVersion p where p.projectId=:project and p.applicationId=:app
          and p.name=:name and p.isActive=true order by p.version desc, p.id asc
        """,
                PromptVersion.class)
            .setParameter("project", scope.projectId())
            .setParameter("app", scope.applicationId())
            .setParameter("name", request.getPromptName())
            .setMaxResults(1)
            .getResultStream()
            .findFirst()
            .orElseThrow(() -> new ApiFailure(404, "No active prompt version found"));
    var route =
        entities
            .createQuery(
                """
        from ModelRoute r where r.projectId=:project and r.applicationId=:app
          and r.environment=:environment and r.isActive=true
          order by r.isDefault desc, r.priority asc, r.id asc
        """,
                ModelRoute.class)
            .setParameter("project", scope.projectId())
            .setParameter("app", scope.applicationId())
            .setParameter("environment", request.getEnvironment())
            .setMaxResults(1)
            .getResultStream()
            .findFirst()
            .orElseThrow(() -> new ApiFailure(404, "No active model route found"));
    if (!"mock".equals(route.getProvider()) || !"mock-llm-small".equals(route.getModelName())) {
      throw new ApiFailure(404, "Unsupported model route");
    }
    if (prompt.getContent().codePointCount(0, prompt.getContent().length()) > 32000) {
      throw new ApiFailure(404, "Prompt configuration exceeds gateway limit");
    }
    return new GatewayContext(
        scope,
        prompt.getId(),
        prompt.getVersion(),
        prompt.getContent(),
        route.getId(),
        route.getProvider(),
        route.getModelName());
  }
}
