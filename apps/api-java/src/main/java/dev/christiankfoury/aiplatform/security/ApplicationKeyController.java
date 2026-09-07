package dev.christiankfoury.aiplatform.security;

import dev.christiankfoury.aiplatform.operator.OperatorPayload;
import dev.christiankfoury.aiplatform.operator.UsageFilter;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/v1/admin")
public class ApplicationKeyController {
  private final ApplicationKeyService keys;

  public ApplicationKeyController(ApplicationKeyService keys) {
    this.keys = keys;
  }

  @GetMapping("/applications/{id}/api-keys")
  public List<ApplicationKeyService.KeyView> list(
      @PathVariable UUID id, @RequestParam(required = false) String limit) {
    return keys.list(id, UsageFilter.limit(limit, 100));
  }

  @PostMapping(value = "/applications/{id}/api-keys", consumes = "application/json")
  @ResponseStatus(HttpStatus.CREATED)
  public ApplicationKeyService.CreatedKey create(@PathVariable UUID id, HttpServletRequest request)
      throws IOException {
    var payload = OperatorPayload.read(request, OperatorPayload.Kind.KEY_CREATE);
    return keys.create(id, payload.text("description"));
  }

  @PostMapping("/api-keys/{id}/revoke")
  public ApplicationKeyService.KeyView revoke(@PathVariable UUID id) {
    return keys.revoke(id);
  }
}
