package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.auth.ApplicationAuthenticator.Scope;
import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.http.ValidationFailure;
import dev.christiankfoury.aiplatform.persistence.repository.ClientApplicationRepository;
import dev.christiankfoury.aiplatform.persistence.repository.ProjectRepository;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TelemetryAttribution {
  private static final Set<String> AGENTOPS_OPERATIONS =
      Set.of("agent_step", "structured_generation", "workflow_summary");
  private final ClientApplicationRepository applications;
  private final ProjectRepository projects;

  public TelemetryAttribution(
      ClientApplicationRepository applications, ProjectRepository projects) {
    this.applications = applications;
    this.projects = projects;
  }

  @Transactional(readOnly = true)
  public void verify(Scope scope, TelemetryEvent event) {
    var application = applications.findById(scope.applicationId()).orElseThrow(() -> denied());
    var project = projects.findById(scope.projectId()).orElseThrow(() -> denied());
    String source = event.text("source_app");
    String expectedApp =
        source.equals("proofbase") ? "enterprise-knowledge-agent" : "agentops-workflow-platform";
    if (!Boolean.TRUE.equals(project.getIsActive())
        || !project.getSlug().equals(source)
        || !application.getSlug().equals(expectedApp)
        || !application.getProjectId().equals(project.getId())
        || !Boolean.TRUE.equals(application.getIsActive())) throw denied();
    if (source.equals("agentops") != AGENTOPS_OPERATIONS.contains(event.text("operation_type")))
      throw new ValidationFailure("operation_type");
  }

  private static ApiFailure denied() {
    return new ApiFailure(403, "API key is not registered for this telemetry source");
  }
}
