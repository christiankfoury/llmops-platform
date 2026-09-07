package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.ApiKey;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ApiKeyRepository extends JpaRepository<ApiKey, UUID> {
  Optional<ApiKey> findByKeyHash(String keyHash);
}
