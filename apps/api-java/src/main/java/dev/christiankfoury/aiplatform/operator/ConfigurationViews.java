package dev.christiankfoury.aiplatform.operator;

import dev.christiankfoury.aiplatform.persistence.model.ModelRoute;
import dev.christiankfoury.aiplatform.persistence.model.PromptVersion;
import java.util.UUID;

public final class ConfigurationViews {
  private ConfigurationViews() {}

  public record Prompt(
      UUID id,
      UUID projectId,
      UUID applicationId,
      String name,
      int version,
      String content,
      boolean isActive) {
    public static Prompt from(PromptVersion value) {
      return new Prompt(
          value.getId(),
          value.getProjectId(),
          value.getApplicationId(),
          value.getName(),
          value.getVersion(),
          value.getContent(),
          value.getIsActive());
    }

    @Override
    public String toString() {
      return "Prompt[content omitted]";
    }
  }

  public record Route(
      UUID id,
      UUID projectId,
      UUID applicationId,
      String environment,
      String provider,
      String modelName,
      int priority,
      boolean isDefault,
      boolean isActive) {
    public static Route from(ModelRoute value) {
      return new Route(
          value.getId(),
          value.getProjectId(),
          value.getApplicationId(),
          value.getEnvironment(),
          value.getProvider(),
          value.getModelName(),
          value.getPriority(),
          value.getIsDefault(),
          value.getIsActive());
    }
  }
}
