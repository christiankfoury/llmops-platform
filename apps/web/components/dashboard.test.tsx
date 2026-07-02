import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { Dashboard } from "./dashboard";

const projectId = "001d4b51-5b43-4c44-aec1-d7373b6bfb48";
const applicationId = "441af473-7f36-47c9-9ad3-b04ab715bf9f";
const promptVersionId = "5ef38aac-e4b3-4d82-a129-853eaa6e9a27";
const modelRouteId = "750ff1c1-6fc6-4097-9740-36d1509da311";

const successfulRequest = {
  id: "0c7671f5-97f2-4d47-a738-2d81932cf6de",
  request_id: "req_testdashboard",
  project_id: projectId,
  project_name: "Demo Project",
  project_slug: "demo-project",
  application_id: applicationId,
  application_name: "Demo App",
  application_slug: "demo-app",
  application_environment: "local",
  prompt_version_id: promptVersionId,
  model_route_id: modelRouteId,
  status: "succeeded",
  provider: "mock",
  model_name: "mock-llm-small",
  latency_ms: 121,
  estimated_input_tokens: 10,
  estimated_output_tokens: 12,
  estimated_cost_usd: "0.000003",
  error_category: null,
  created_at: "2026-06-30T00:00:00Z"
};

const failedRequest = {
  id: "c0164bfd-9a2c-4a90-a902-1fbe411e40af",
  request_id: "req_failedtest",
  project_id: projectId,
  project_name: "Demo Project",
  project_slug: "demo-project",
  application_id: applicationId,
  application_name: "Demo App",
  application_slug: "demo-app",
  application_environment: "local",
  prompt_version_id: promptVersionId,
  model_route_id: modelRouteId,
  status: "failed",
  provider: "mock",
  model_name: "mock-llm-small",
  latency_ms: 50,
  estimated_input_tokens: null,
  estimated_output_tokens: null,
  estimated_cost_usd: null,
  error_category: "provider_error",
  created_at: "2026-06-30T00:01:00Z"
};

let requestedPaths: string[] = [];

beforeEach(() => {
  requestedPaths = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = input.toString();
      const path = url.startsWith("/")
        ? url
        : new URL(url).pathname + new URL(url).search;
      requestedPaths.push(path);

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(responseFor(path))
      });
    })
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("renders scopes, filters, and dashboard data from API responses", async () => {
  render(<Dashboard />);

  await screen.findByText("42");

  screen.getByLabelText("Project");
  screen.getByLabelText("Application");
  screen.getByLabelText("Date range");
  screen.getByText("Demo Project");
  screen.getByText("Demo App (local)");
  screen.getByText("3");
  screen.getByText("123 ms");
  screen.getByText("$0.012345");
  screen.getByText("http://api.test");
  screen.getAllByText("mock-llm-small");
  screen.getAllByText("provider_error");
  screen.getByText("default-chat");
});

test("changing filters calls backend usage URLs with selected query params", async () => {
  render(<Dashboard />);

  await screen.findByText("42");
  fireEvent.change(screen.getByLabelText("Project"), { target: { value: projectId } });
  await waitFor(() =>
    expect(
      requestedPaths.some(
        (path) => path.startsWith("/v1/usage/summary?") && path.includes(`project_id=${projectId}`)
      )
    ).toBe(true)
  );

  fireEvent.change(screen.getByLabelText("Application"), { target: { value: applicationId } });
  await waitFor(() =>
    expect(
      requestedPaths.some(
        (path) =>
          path.startsWith("/v1/usage/requests?") &&
          path.includes(`project_id=${projectId}`) &&
          path.includes(`application_id=${applicationId}`)
      )
    ).toBe(true)
  );
});

test("filtered empty results show the filtered empty state", async () => {
  render(<Dashboard />);

  await screen.findByText("42");
  fireEvent.change(screen.getByLabelText("Status"), { target: { value: "failed" } });

  await screen.findByText("No matching requests");
});

test("clicking a failed request opens the detail panel with error details", async () => {
  render(<Dashboard />);

  await screen.findByText("42");
  fireEvent.click(screen.getByRole("button", { name: "req_failedte" }));

  const detailPanel = screen.getByLabelText("Request details");
  within(detailPanel).getByText("Request Detail");
  expect(within(detailPanel).getAllByText("req_failedtest")).toHaveLength(2);
  within(detailPanel).getByText("provider_error");
  within(detailPanel).getByText(modelRouteId);
});

function responseFor(path: string): unknown {
  if (path === "/api/runtime-config") {
    return {
      apiBaseUrl: "http://api.test"
    };
  }

  if (path.startsWith("/v1/usage/summary")) {
    if (path.includes("status=failed")) {
      return {
        request_count: 1,
        error_count: 1,
        average_latency_ms: 50,
        estimated_cost_usd: "0.000000"
      };
    }
    return {
      request_count: 42,
      error_count: 3,
      average_latency_ms: 123.4,
      estimated_cost_usd: "0.012345"
    };
  }

  if (path.startsWith("/v1/usage/requests")) {
    return path.includes("status=failed") ? [] : [successfulRequest];
  }

  if (path.startsWith("/v1/usage/errors")) {
    return [failedRequest];
  }

  if (path === "/v1/usage/scopes") {
    return [
      {
        id: projectId,
        name: "Demo Project",
        slug: "demo-project",
        applications: [
          {
            id: applicationId,
            name: "Demo App",
            slug: "demo-app",
            environment: "local"
          }
        ]
      }
    ];
  }

  if (path === "/v1/admin/prompt-versions") {
    return [
      {
        id: promptVersionId,
        project_id: projectId,
        application_id: applicationId,
        name: "default-chat",
        version: 1,
        content: "Prompt",
        is_active: true
      }
    ];
  }

  if (path === "/v1/admin/model-routes") {
    return [
      {
        id: modelRouteId,
        project_id: projectId,
        application_id: applicationId,
        environment: "local",
        provider: "mock",
        model_name: "mock-llm-small",
        priority: 100,
        is_default: true,
        is_active: true
      }
    ];
  }

  return {};
}
