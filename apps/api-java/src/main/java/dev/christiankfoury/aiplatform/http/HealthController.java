package dev.christiankfoury.aiplatform.http;

import java.util.Map;
import org.springframework.boot.availability.ApplicationAvailability;
import org.springframework.boot.availability.LivenessState;
import org.springframework.boot.availability.ReadinessState;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  private final ApplicationAvailability availability;

  private final dev.christiankfoury.aiplatform.reliability.DependencyReadiness dependencies;

  public HealthController(
      ApplicationAvailability availability,
      dev.christiankfoury.aiplatform.reliability.DependencyReadiness dependencies) {
    this.availability = availability;
    this.dependencies = dependencies;
  }

  @GetMapping("/health")
  public Map<String, String> health() {
    return Map.of("status", "ok", "service", "api");
  }

  @GetMapping("/health/live")
  public ResponseEntity<Map<String, String>> live() {
    boolean healthy = availability.getLivenessState() == LivenessState.CORRECT;
    return ResponseEntity.status(healthy ? 200 : 503)
        .body(Map.of("status", healthy ? "ok" : "unavailable"));
  }

  @GetMapping("/health/ready")
  public ResponseEntity<Map<String, String>> ready() {
    boolean ready =
        availability.getReadinessState() == ReadinessState.ACCEPTING_TRAFFIC
            && dependencies.ready();
    return ResponseEntity.status(ready ? 200 : 503)
        .body(Map.of("status", ready ? "ready" : "unavailable"));
  }
}
