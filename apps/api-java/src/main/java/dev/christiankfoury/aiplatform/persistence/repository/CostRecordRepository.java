package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.CostRecord;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CostRecordRepository extends JpaRepository<CostRecord, UUID> {
  Optional<CostRecord> findByGatewayRequestId(UUID gatewayRequestId);
}
