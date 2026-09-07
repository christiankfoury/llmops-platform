package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.ModelRoute;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ModelRouteRepository extends JpaRepository<ModelRoute, UUID> {
  Optional<ModelRoute> findFirstByProjectIdAndApplicationIdAndEnvironmentAndProviderAndModelName(
      UUID projectId, UUID applicationId, String environment, String provider, String modelName);
}
