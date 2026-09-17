import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { Dashboard } from "./dashboard";

const projectId = "001d4b51-5b43-4c44-aec1-d7373b6bfb48";
const applicationId = "441af473-7f36-47c9-9ad3-b04ab715bf9f";
const proofbaseProjectId = "12e4dc71-a556-45f8-a506-b7d2cae10002";
const proofbaseApplicationId = "13003f0d-42fd-4543-bf17-399e06ef0002";
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
  source_app: null,
  operation_type: null,
  external_event_id: null,
  external_request_id: null,
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
  source_app: null,
  operation_type: null,
  external_event_id: null,
  external_request_id: null,
  created_at: "2026-06-30T00:01:00Z"
};

const proofbaseTelemetryRequest = {
  id: "20ec6db2-7b46-4980-839f-a37fdd7f5db2",
  request_id: "ext_proofbase1",
  project_id: proofbaseProjectId,
  project_name: "Proofbase",
  project_slug: "proofbase",
  application_id: proofbaseApplicationId,
  application_name: "Enterprise Knowledge Agent",
  application_slug: "enterprise-knowledge-agent",
  application_environment: "local",
  prompt_version_id: null,
  model_route_id: null,
  status: "succeeded",
  provider: "openai",
  model_name: "gpt-4.1-mini",
  latency_ms: 1830,
  estimated_input_tokens: 1200,
  estimated_output_tokens: 340,
  estimated_cost_usd: "0.000812",
  error_category: null,
  source_app: "proofbase",
  operation_type: "rag_query",
  external_event_id: "evt_proofbase_001",
  external_request_id: "proofbase_req_001",
  created_at: "2026-07-06T00:00:00Z"
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
  expect(screen.queryByText("http://api.test")).not.toBeInTheDocument();
  screen.getAllByText("mock-llm-small");
  screen.getAllByText("proofbase");
  screen.getAllByText("Rag Query");
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

test("source app filter requests Proofbase telemetry and renders event details", async () => {
  render(<Dashboard />);

  await screen.findByText("42");
  fireEvent.change(screen.getByLabelText("Source app"), { target: { value: "proofbase" } });

  await waitFor(() =>
    expect(
      requestedPaths.some(
        (path) =>
          path.startsWith("/v1/usage/requests?") && path.includes("source_app=proofbase")
      )
    ).toBe(true)
  );

  await screen.findAllByText("Proofbase");
  fireEvent.click(screen.getByRole("button", { name: "ext_proofbase1" }));

  const detailPanel = screen.getByLabelText("Request details");
  within(detailPanel).getByText("Telemetry reported by proofbase.", { exact: false });
  within(detailPanel).getByText("Rag Query");
  within(detailPanel).getAllByText("evt_proofbase_001");
  within(detailPanel).getAllByText("proofbase_req_001");
  within(detailPanel).getByText("1200 in / 340 out");
  within(detailPanel).getByText("$0.000812");
});

test("operation filter is included in backend usage URLs", async () => {
  render(<Dashboard />);

  await screen.findByText("42");
  fireEvent.change(screen.getByLabelText("Operation"), { target: { value: "rag_query" } });

  await waitFor(() =>
    expect(
      requestedPaths.some(
        (path) =>
          path.startsWith("/v1/usage/summary?") && path.includes("operation_type=rag_query")
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
  fireEvent.click(screen.getByRole("button", { name: "req_failedtest" }));

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
    if (path.includes("source_app=proofbase") || path.includes("operation_type=rag_query")) {
      return {
        request_count: 1,
        error_count: 0,
        average_latency_ms: 1830,
        estimated_cost_usd: "0.000812"
      };
    }
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
    if (path.includes("status=failed")) {
      return [];
    }
    if (path.includes("source_app=proofbase") || path.includes("operation_type=rag_query")) {
      return [proofbaseTelemetryRequest];
    }
    return [successfulRequest, proofbaseTelemetryRequest];
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
      },
      {
        id: proofbaseProjectId,
        name: "Proofbase",
        slug: "proofbase",
        applications: [
          {
            id: proofbaseApplicationId,
            name: "Enterprise Knowledge Agent",
            slug: "enterprise-knowledge-agent",
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
    ,
      {
        id: "4ea688a8-a9f1-4f57-a407-9a46cb617e6b",
        project_id: proofbaseProjectId,
        application_id: proofbaseApplicationId,
        name: "proofbase-external-telemetry",
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
    ,
      {
        id: "6c2fdf6c-79c0-4e1c-9418-a775805873eb",
        project_id: proofbaseProjectId,
        application_id: proofbaseApplicationId,
        environment: "local",
        provider: "external",
        model_name: "reported-by-proofbase",
        priority: 100,
        is_default: true,
        is_active: true
      }
    ];
  }

  return {};
}
