package dev.christiankfoury.aiplatform.gateway;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GatewayController {
  private final GatewayService gateway;

  public GatewayController(GatewayService gateway) {
    this.gateway = gateway;
  }

  @PostMapping("/v1/gateway/completions")
  public CompletionResponse complete(
      @RequestHeader(value = "X-API-Key", required = false) String key,
      @Valid @RequestBody CompletionRequest request) {
    return gateway.complete(key, request);
  }
}
