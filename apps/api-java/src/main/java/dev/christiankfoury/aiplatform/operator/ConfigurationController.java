package dev.christiankfoury.aiplatform.operator;

import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/v1/admin")
public class ConfigurationController {
  private final ConfigurationService configuration;

  public ConfigurationController(ConfigurationService configuration) {
    this.configuration = configuration;
  }

  @GetMapping("/prompt-versions")
  public List<ConfigurationViews.Prompt> prompts(@RequestParam(required = false) String limit) {
    return configuration.prompts(UsageFilter.limit(limit, 100));
  }

  @PostMapping(value = "/prompt-versions", consumes = "application/json")
  @ResponseStatus(HttpStatus.CREATED)
  public ConfigurationViews.Prompt createPrompt(HttpServletRequest request) throws IOException {
    return configuration.createPrompt(
        OperatorPayload.read(request, OperatorPayload.Kind.PROMPT_CREATE));
  }

  @PatchMapping(value = "/prompt-versions/{id}", consumes = "application/json")
  public ConfigurationViews.Prompt updatePrompt(@PathVariable UUID id, HttpServletRequest request)
      throws IOException {
    return configuration.updatePrompt(
        id, OperatorPayload.read(request, OperatorPayload.Kind.PROMPT_UPDATE));
  }

  @PostMapping("/prompt-versions/{id}/activate")
  public ConfigurationViews.Prompt activatePrompt(@PathVariable UUID id) {
    return configuration.activatePrompt(id);
  }

  @GetMapping("/model-routes")
  public List<ConfigurationViews.Route> routes(@RequestParam(required = false) String limit) {
    return configuration.routes(UsageFilter.limit(limit, 100));
  }

  @PostMapping(value = "/model-routes", consumes = "application/json")
  @ResponseStatus(HttpStatus.CREATED)
  public ConfigurationViews.Route createRoute(HttpServletRequest request) throws IOException {
    return configuration.createRoute(
        OperatorPayload.read(request, OperatorPayload.Kind.ROUTE_CREATE));
  }

  @PatchMapping(value = "/model-routes/{id}", consumes = "application/json")
  public ConfigurationViews.Route updateRoute(@PathVariable UUID id, HttpServletRequest request)
      throws IOException {
    return configuration.updateRoute(
        id, OperatorPayload.read(request, OperatorPayload.Kind.ROUTE_UPDATE));
  }

  @PostMapping("/model-routes/{id}/activate")
  public ConfigurationViews.Route activateRoute(@PathVariable UUID id) {
    return configuration.activateRoute(id);
  }
}
