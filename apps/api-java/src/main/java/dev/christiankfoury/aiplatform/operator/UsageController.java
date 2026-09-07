package dev.christiankfoury.aiplatform.operator;

import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/usage")
public class UsageController {
  private final UsageQueries queries;

  public UsageController(UsageQueries queries) {
    this.queries = queries;
  }

  @GetMapping("/summary")
  public UsageQueries.Summary summary(HttpServletRequest request) {
    return queries.summary(UsageFilter.parse(request.getParameterMap(), false));
  }

  @GetMapping("/requests")
  public List<Map<String, Object>> requests(HttpServletRequest request) {
    return queries.requests(UsageFilter.parse(request.getParameterMap(), false));
  }

  @GetMapping("/errors")
  public List<Map<String, Object>> errors(HttpServletRequest request) {
    return queries.requests(UsageFilter.parse(request.getParameterMap(), true));
  }

  @GetMapping("/scopes")
  public List<UsageQueries.ProjectScope> scopes() {
    return queries.scopes();
  }
}
