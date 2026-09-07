package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.PromptVersion;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromptVersionRepository extends JpaRepository<PromptVersion, UUID> {
  Optional<PromptVersion> findByProjectIdAndApplicationIdAndNameAndVersion(
      UUID projectId, UUID applicationId, String name, Integer version);
}
