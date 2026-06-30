import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, test, vi } from "vitest";

import { Dashboard } from "./dashboard";

const responses: Record<string, unknown> = {
  "/api/runtime-config": {
    apiBaseUrl: "http://api.test"
  },
  "/v1/usage/summary": {
    request_count: 42,
    error_count: 3,
    average_latency_ms: 123.4,
    estimated_cost_usd: "0.012345"
  },
  "/v1/usage/requests?limit=12": [
    {
      id: "0c7671f5-97f2-4d47-a738-2d81932cf6de",
      request_id: "req_testdashboard",
      status: "succeeded",
      provider: "mock",
      model_name: "mock-llm-small",
      latency_ms: 121,
      estimated_input_tokens: 10,
      estimated_output_tokens: 12,
      estimated_cost_usd: "0.000003",
      error_category: null,
      created_at: "2026-06-30T00:00:00Z"
    }
  ],
  "/v1/usage/errors?limit=8": [
    {
      id: "c0164bfd-9a2c-4a90-a902-1fbe411e40af",
      request_id: "req_failedtest",
      status: "failed",
      provider: "mock",
      model_name: "mock-llm-small",
      latency_ms: 50,
      estimated_input_tokens: null,
      estimated_output_tokens: null,
      estimated_cost_usd: null,
      error_category: "provider_error",
      created_at: "2026-06-30T00:00:00Z"
    }
  ],
  "/v1/admin/prompt-versions": [
    {
      id: "5ef38aac-e4b3-4d82-a129-853eaa6e9a27",
      project_id: "001d4b51-5b43-4c44-aec1-d7373b6bfb48",
      application_id: "441af473-7f36-47c9-9ad3-b04ab715bf9f",
      name: "default-chat",
      version: 1,
      content: "Prompt",
      is_active: true
    }
  ],
  "/v1/admin/model-routes": [
    {
      id: "750ff1c1-6fc6-4097-9740-36d1509da311",
      project_id: "001d4b51-5b43-4c44-aec1-d7373b6bfb48",
      application_id: "441af473-7f36-47c9-9ad3-b04ab715bf9f",
      environment: "local",
      provider: "mock",
      model_name: "mock-llm-small",
      priority: 100,
      is_default: true,
      is_active: true
    }
  ]
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = input.toString();
      const path = url.startsWith("/")
        ? url
        : new URL(url).pathname + new URL(url).search;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(responses[path])
      });
    })
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("renders dashboard data from API responses", async () => {
  render(<Dashboard />);

  await screen.findByText("42");

  screen.getByText("3");
  screen.getByText("123 ms");
  screen.getByText("$0.012345");
  screen.getByText("http://api.test");
  screen.getAllByText("mock-llm-small");
  screen.getByText("provider_error");
  screen.getByText("default-chat");
});
