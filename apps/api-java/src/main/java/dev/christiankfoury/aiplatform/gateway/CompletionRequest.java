package dev.christiankfoury.aiplatform.gateway;

import dev.christiankfoury.aiplatform.http.StrictStringDeserializer;
import jakarta.validation.constraints.NotNull;
import org.hibernate.validator.constraints.CodePointLength;
import tools.jackson.databind.annotation.JsonDeserialize;

public class CompletionRequest {
  @JsonDeserialize(using = StrictStringDeserializer.class)
  @NotNull
  @CodePointLength(min = 1, max = 8000)
  private String input;

  @JsonDeserialize(using = StrictStringDeserializer.class)
  @NotNull
  @CodePointLength(min = 1, max = 160)
  private String promptName = "default-chat";

  @JsonDeserialize(using = StrictStringDeserializer.class)
  @NotNull
  @CodePointLength(min = 1, max = 40)
  private String environment = "local";

  public String getInput() {
    return input;
  }

  public void setInput(String value) {
    input = value;
  }

  public String getPromptName() {
    return promptName;
  }

  public void setPromptName(String value) {
    promptName = value;
  }

  public String getEnvironment() {
    return environment;
  }

  public void setEnvironment(String value) {
    environment = value;
  }
}
