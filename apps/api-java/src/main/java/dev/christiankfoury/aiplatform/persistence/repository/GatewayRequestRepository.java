package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.GatewayRequest;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GatewayRequestRepository extends JpaRepository<GatewayRequest, UUID> {
  Optional<GatewayRequest> findByApplicationIdAndExternalEventId(
      UUID applicationId, String externalEventId);
}
