package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.AuditLog;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {
  Optional<AuditLog> findFirstByProjectIdAndApplicationIdAndActionAndResourceId(
      UUID projectId, UUID applicationId, String action, String resourceId);
}
