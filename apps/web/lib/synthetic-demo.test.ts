import { expect, test } from "vitest";
import { syntheticDemo } from "./synthetic-demo";

type Row = { id: string; request_id: string; project_id: string; application_id: string; status: string; latency_ms: number; estimated_cost_usd: string; created_at: string; prompt_version_id: string; model_route_id: string };
const rows = (query = "", endpoint = "requests") => syntheticDemo(`v1/usage/${endpoint}`, new URLSearchParams(query)) as Row[];
const summary = (query = "") => syntheticDemo("v1/usage/summary", new URLSearchParams(query));

test("examples form one coherent dataset with scoped configuration and consistent totals", () => {
  const all = rows();
  expect(all).toHaveLength(12);
  expect(new Set(all.map((row) => row.request_id)).size).toBe(12);
  expect(new Set(all.map((row) => row.project_id)).size).toBe(3);
  expect(summary()).toEqual({ request_count: 12, error_count: 3, average_latency_ms: 5068 / 12, estimated_cost_usd: "0.002585" });
  expect(rows("", "errors").map((row) => row.status)).toEqual(["failed", "failed", "failed"]);
  const prompts = syntheticDemo("v1/admin/prompt-versions", new URLSearchParams()) as Row[];
  const routes = syntheticDemo("v1/admin/model-routes", new URLSearchParams()) as Row[];
  for (const row of all) {
    expect(prompts.find((prompt) => prompt.id === row.prompt_version_id)?.project_id).toBe(row.project_id);
    expect(routes.find((route) => route.id === row.model_route_id)?.application_id).toBe(row.application_id);
  }
});

test("combined filters narrow rows and summaries without leaking another scope", () => {
  const query = `project_id=${rows()[0].project_id}&status=succeeded`;
  expect(rows(query)).toHaveLength(4);
  expect(summary(query)).toMatchObject({ request_count: 4, error_count: 0 });
  expect(rows("source_app=agentops&status=failed")).toHaveLength(2);
  expect(rows("error_category=provider_timeout")).toHaveLength(1);
  expect(rows("source_app=proofbase&operation_type=agent_step")).toEqual([]);
  expect(rows("project_id=unknown")).toEqual([]);
  expect(summary("project_id=unknown")).toEqual({ request_count: 0, error_count: 0, average_latency_ms: 0, estimated_cost_usd: "0.000000" });
});

test("date boundaries are inclusive and fixed examples remain deterministic", () => {
  const stamp = rows()[0].created_at;
  expect(rows(`created_from=${stamp}&created_to=${stamp}`)).toHaveLength(1);
  expect(rows("created_from=invalid")).toEqual([]);
  expect(rows("created_from=2099-01-01")).toEqual([]);
  expect(rows().map((row) => row.created_at)).toEqual(rows().map((row) => row.created_at).sort().reverse());
});

test("failure lists ignore status while retaining the other Java API filters", () => {
  expect(rows("status=succeeded", "errors")).toEqual(rows("", "errors"));
  expect(rows("status=succeeded&source_app=agentops&limit=1", "errors")).toHaveLength(1);
  expect(rows("status=succeeded&source_app=agentops", "errors").every((row) => row.status === "failed")).toBe(true);
  expect(summary("status=succeeded")).toMatchObject({ request_count: 9, error_count: 0 });
});

test("limits apply to lists after filtering and never alter summary totals", () => {
  expect(rows("status=failed&limit=1")).toHaveLength(1);
  expect(rows("limit=1", "errors")).toHaveLength(1);
  expect(summary("limit=1")).toEqual(summary());
  for (const value of ["0", "-1", "1.5", "invalid"]) expect(rows(`limit=${value}`)).toEqual([]);
  expect(rows("limit=100")).toHaveLength(12);
  expect(syntheticDemo("v1/admin/api-keys", new URLSearchParams())).toBeUndefined();
});
