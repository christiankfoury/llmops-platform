package dev.christiankfoury.aiplatform.persistence.repository;

import dev.christiankfoury.aiplatform.persistence.model.Project;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProjectRepository extends JpaRepository<Project, UUID> {
  Optional<Project> findBySlug(String slug);
}
