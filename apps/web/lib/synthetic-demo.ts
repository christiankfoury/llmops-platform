// Fixed, invented examples. This module has no backend, identity, database, or provider client.
const uuid = (value: number) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;
const scopes = [
  { name: "Gateway Demo", slug: "gateway-demo", application: "Support assistant", source: null },
  { name: "Proofbase Demo", slug: "proofbase-demo", application: "Knowledge search", source: "proofbase" },
  { name: "AgentOps Demo", slug: "agentops-demo", application: "Document workflow", source: "agentops" }
].map((scope, index) => ({
  ...scope, id: uuid(index + 1), applicationId: uuid(index + 11)
}));

const latency = [184, 326, 242, 209, 2000, 412, 168, 287, 15, 351, 224, 650];
const failures: Record<number, string> = { 4: "provider_timeout", 8: "rate_limit_exceeded", 11: "provider_error" };
const requests = latency.map((latencyMs, index) => {
  const scope = scopes[index % scopes.length];
  const error = failures[index] ?? null;
  const costUnits = error ? 0 : 120 + index * 35;
  return {
    id: uuid(index + 101), request_id: `demo-request-${String(index + 1).padStart(3, "0")}`,
    project_id: scope.id, project_name: scope.name, project_slug: scope.slug,
    application_id: scope.applicationId, application_name: scope.application,
    application_slug: scope.slug, application_environment: "demo",
    prompt_version_id: uuid(index % 3 + 201), model_route_id: uuid(index % 3 + 301),
    status: error ? "failed" : "succeeded", provider: "mock",
    model_name: "mock-llm-small", latency_ms: latencyMs,
    estimated_input_tokens: error ? 0 : 160 + index * 23,
    estimated_output_tokens: error ? 0 : 80 + index * 17,
    estimated_cost_usd: (costUnits / 1_000_000).toFixed(6), error_category: error,
    source_app: scope.source,
    operation_type: scope.source === "agentops" ? "agent_step" : scope.source === "proofbase" ? "chat" : null,
    external_event_id: scope.source ? `demo-event-${index + 1}` : null,
    external_request_id: scope.source ? `demo-client-request-${index + 1}` : null,
    created_at: `2026-09-17T10:${String(30 - index).padStart(2, "0")}:00Z`
  };
});

function matchingRequests(query: URLSearchParams) {
  return requests.filter((request) => [...query.entries()].every(([key, value]) => {
    if (key === "limit") return true;
    if (key === "created_from") return new Date(request.created_at) >= new Date(value);
    if (key === "created_to") return new Date(request.created_at) <= new Date(value);
    return key in request && String(request[key as keyof typeof request]) === value;
  }));
}

function limited<T>(rows: T[], query: URLSearchParams) {
  const value = query.get("limit");
  if (value === null) return rows;
  // An invalid limit produces no example rows; it never opens a backend fallback.
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value))) return [];
  return rows.slice(0, Math.min(Number(value), requests.length));
}

export function syntheticDemo(path: string, query: URLSearchParams): unknown {
  const matching = matchingRequests(query);
  switch (path) {
    case "v1/usage/summary": return {
      request_count: matching.length,
      error_count: matching.filter((request) => request.status === "failed").length,
      average_latency_ms: matching.length ? matching.reduce((sum, request) => sum + request.latency_ms, 0) / matching.length : 0,
      estimated_cost_usd: (matching.reduce((sum, request) => sum + Math.round(Number(request.estimated_cost_usd) * 1_000_000), 0) / 1_000_000).toFixed(6)
    };
    case "v1/usage/requests": return limited(matching, query);
    case "v1/usage/errors": return limited(matching.filter((request) => request.status === "failed"), query);
    case "v1/usage/scopes": return scopes.map((scope) => ({
      id: scope.id, name: scope.name, slug: scope.slug,
      applications: [{ id: scope.applicationId, name: scope.application, slug: scope.slug, environment: "demo" }]
    }));
    case "v1/admin/prompt-versions": return scopes.map((scope, index) => ({
      id: uuid(index + 201), project_id: scope.id, application_id: scope.applicationId,
      name: ["Support response", "Search summary", "Document classification"][index], version: index + 1, is_active: true
    }));
    case "v1/admin/model-routes": return scopes.map((scope, index) => ({
      id: uuid(index + 301), project_id: scope.id, application_id: scope.applicationId,
      environment: "demo", provider: "mock", model_name: "mock-llm-small",
      priority: 100, is_default: true, is_active: true
    }));
    default: return undefined;
  }
}
