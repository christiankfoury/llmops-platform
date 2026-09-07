package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.OperatorProjectGrant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OperatorProjectGrantRepository extends JpaRepository<OperatorProjectGrant, UUID> {
  Optional<OperatorProjectGrant> findByIssuerAndSubjectAndProjectId(
      String issuer, String subject, UUID projectId);
}
