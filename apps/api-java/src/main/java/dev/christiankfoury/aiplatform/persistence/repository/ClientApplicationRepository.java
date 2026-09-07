package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.ClientApplication;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ClientApplicationRepository extends JpaRepository<ClientApplication, UUID> {
  Optional<ClientApplication> findByProjectIdAndSlug(UUID projectId, String slug);
}
