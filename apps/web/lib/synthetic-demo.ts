// This module contains fixed fixtures only and has no backend, identity, database, or provider client.
const project = "00000000-0000-4000-8000-000000000001";
const application = "00000000-0000-4000-8000-000000000002";
const request = {
  id: "00000000-0000-4000-8000-000000000003", request_id: "synthetic-demo-request",
  project_id: project, project_name: "Synthetic Demo", project_slug: "synthetic-demo",
  application_id: application, application_name: "Example client", application_slug: "example-client",
  application_environment: "demo", prompt_version_id: null, model_route_id: null,
  status: "succeeded", provider: "mock", model_name: "mock-llm-small", latency_ms: 120,
  estimated_input_tokens: 10, estimated_output_tokens: 20, estimated_cost_usd: "0.000005",
  error_category: null, source_app: null, operation_type: null, external_event_id: null,
  external_request_id: null, created_at: "2026-09-01T12:00:00Z"
};
export function syntheticDemo(path: string, query: URLSearchParams): unknown {
  const matches = [...query.entries()].every(([key, value]) => {
    if (key === "limit") return true;
    if (key === "created_from") return new Date(request.created_at) >= new Date(value);
    if (key === "created_to") return new Date(request.created_at) <= new Date(value);
    return key in request && String(request[key as keyof typeof request]) === value;
  });
  switch (path) {
    case "v1/usage/summary": return matches ? { request_count: 1, error_count: 0, average_latency_ms: 120, estimated_cost_usd: "0.000005" } :
      { request_count: 0, error_count: 0, average_latency_ms: 0, estimated_cost_usd: "0.000000" };
    case "v1/usage/requests": return matches ? [request] : [];
    case "v1/usage/errors": return [];
    case "v1/usage/scopes": return [{ id: project, name: "Synthetic Demo", slug: "synthetic-demo",
      applications: [{ id: application, name: "Example client", slug: "example-client", environment: "demo" }] }];
    case "v1/admin/prompt-versions": return [];
    case "v1/admin/model-routes": return [];
    default: return undefined;
  }
}
