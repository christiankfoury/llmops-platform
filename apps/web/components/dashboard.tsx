"use client";

import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import styles from "./dashboard.module.css";

type UsageSummary = {
  request_count: number;
  error_count: number;
  average_latency_ms: number;
  estimated_cost_usd: string;
};

type GatewayRequest = {
  id: string;
  request_id: string;
  project_id: string;
  project_name: string | null;
  project_slug: string | null;
  application_id: string;
  application_name: string | null;
  application_slug: string | null;
  application_environment: string | null;
  prompt_version_id: string | null;
  model_route_id: string | null;
  status: string;
  provider: string | null;
  model_name: string | null;
  latency_ms: number | null;
  estimated_input_tokens: number | null;
  estimated_output_tokens: number | null;
  estimated_cost_usd: string | null;
  error_category: string | null;
  source_app: string | null;
  operation_type: string | null;
  external_event_id: string | null;
  external_request_id: string | null;
  created_at: string;
};

type PromptVersion = {
  id: string;
  project_id: string;
  application_id: string;
  name: string;
  version: number;
  is_active: boolean;
};

type ModelRoute = {
  id: string;
  project_id: string;
  application_id: string;
  environment: string;
  provider: string;
  model_name: string;
  priority: number;
  is_default: boolean;
  is_active: boolean;
};

type ApplicationScope = {
  id: string;
  name: string;
  slug: string;
  environment: string;
};

type ProjectScope = {
  id: string;
  name: string;
  slug: string;
  applications: ApplicationScope[];
};

type DashboardData = {
  summary: UsageSummary;
  requests: GatewayRequest[];
  errors: GatewayRequest[];
  prompts: PromptVersion[];
  routes: ModelRoute[];
  scopes: ProjectScope[];
};

type RuntimeConfig = {
  apiBaseUrl: string;
};

type DatePreset = "all" | "1h" | "24h" | "7d" | "30d" | "custom";

type DashboardFilters = {
  projectId: string;
  applicationId: string;
  status: string;
  provider: string;
  modelName: string;
  sourceApp: string;
  operationType: string;
  errorCategory: string;
  datePreset: DatePreset;
  createdFrom: string;
  createdTo: string;
};

const defaultFilters: DashboardFilters = {
  projectId: "",
  applicationId: "",
  status: "",
  provider: "",
  modelName: "",
  sourceApp: "",
  operationType: "",
  errorCategory: "",
  datePreset: "all",
  createdFrom: "",
  createdTo: ""
};

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;

async function getJson<T>(
  apiBaseUrl: string,
  path: string,
  signal: AbortSignal
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { signal });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return (await response.json()) as T;
}

async function getRuntimeConfig(signal: AbortSignal): Promise<RuntimeConfig> {
  const response = await fetch("/api/runtime-config", { signal });
  if (!response.ok) {
    throw new Error(`runtime config returned ${response.status}`);
  }
  return (await response.json()) as RuntimeConfig;
}

export function Dashboard() {
  const [apiBaseUrl, setApiBaseUrl] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const [selectedRequest, setSelectedRequest] = useState<GatewayRequest | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadConfig() {
      try {
        const config = await getRuntimeConfig(controller.signal);
        setApiBaseUrl(config.apiBaseUrl);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setLoadState("error");
        setMessage(error instanceof Error ? error.message : "Runtime config load failed");
      }
    }

    loadConfig();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (apiBaseUrl == null) {
      return;
    }

    const apiUrl = apiBaseUrl;
    let stopped = false;
    let activeController: AbortController | null = null;
    const filterQuery = buildFilterQuery(filters);
    const requestPath = buildPath("/v1/usage/requests", filterQuery, { limit: "12" });
    const errorPath = buildPath("/v1/usage/errors", filterQuery, { limit: "8" });

    async function loadDashboard() {
      if (activeController != null) {
        return;
      }

      const controller = new AbortController();
      activeController = controller;
      setLoadState("loading");
      try {
        const [summary, requests, errors, prompts, routes, scopes] = await Promise.all([
          getJson<UsageSummary>(
            apiUrl,
            buildPath("/v1/usage/summary", filterQuery),
            controller.signal
          ),
          getJson<GatewayRequest[]>(apiUrl, requestPath, controller.signal),
          getJson<GatewayRequest[]>(apiUrl, errorPath, controller.signal),
          getJson<PromptVersion[]>(apiUrl, "/v1/admin/prompt-versions", controller.signal),
          getJson<ModelRoute[]>(apiUrl, "/v1/admin/model-routes", controller.signal),
          getJson<ProjectScope[]>(apiUrl, "/v1/usage/scopes", controller.signal)
        ]);

        if (stopped || controller.signal.aborted) {
          return;
        }
        setData({ summary, requests, errors, prompts, routes, scopes });
        setLoadState("ready");
      } catch (error) {
        if (stopped || controller.signal.aborted) {
          return;
        }
        setLoadState("error");
        setMessage(error instanceof Error ? error.message : "Dashboard load failed");
      } finally {
        if (activeController === controller) {
          activeController = null;
        }
      }
    }

    void loadDashboard();
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }, DASHBOARD_REFRESH_INTERVAL_MS);

    return () => {
      stopped = true;
      window.clearInterval(intervalId);
      activeController?.abort();
    };
  }, [apiBaseUrl, filters]);

  const selectedProject = data?.scopes.find((project) => project.id === filters.projectId);
  const selectableApplications =
    selectedProject?.applications ?? data?.scopes.flatMap((project) => project.applications) ?? [];
  const activeFilterCount = countActiveFilters(filters);
  const hasFilters = activeFilterCount > 0;

  const providerOptions = useMemo(
    () =>
      uniqueSorted([
        ...(data?.routes.map((route) => route.provider) ?? []),
        ...(data?.requests.map((request) => request.provider ?? "") ?? []),
        ...(data?.errors.map((request) => request.provider ?? "") ?? [])
      ]),
    [data]
  );

  const modelOptions = useMemo(
    () =>
      uniqueSorted([
        ...(data?.routes.map((route) => route.model_name) ?? []),
        ...(data?.requests.map((request) => request.model_name ?? "") ?? []),
        ...(data?.errors.map((request) => request.model_name ?? "") ?? [])
      ]),
    [data]
  );

  const errorOptions = useMemo(
    () =>
      uniqueSorted([
        "provider_error",
        ...(data?.errors.map((request) => request.error_category ?? "") ?? [])
      ]),
    [data]
  );
  const sourceAppOptions = useMemo(
    () =>
      uniqueSorted([
        ...(data?.requests.map((request) => request.source_app ?? "") ?? []),
        ...(data?.errors.map((request) => request.source_app ?? "") ?? [])
      ]),
    [data]
  );
  const operationOptions = useMemo(
    () =>
      uniqueSorted([
        ...(data?.requests.map((request) => request.operation_type ?? "") ?? []),
        ...(data?.errors.map((request) => request.operation_type ?? "") ?? [])
      ]),
    [data]
  );

  const visiblePrompts = useMemo(
    () => filterConfigRows(data?.prompts ?? [], filters),
    [data, filters]
  );
  const visibleRoutes = useMemo(() => filterConfigRows(data?.routes ?? [], filters), [data, filters]);

  function updateFilter(name: keyof DashboardFilters, value: string) {
    setSelectedRequest(null);
    setFilters((current) => {
      const next = { ...current, [name]: value };
      if (name === "projectId") {
        next.applicationId = "";
      }
      return next;
    });
  }

  const content = (() => {
    if (loadState === "loading" && data == null) {
      return <div className={styles.notice}>Loading platform data</div>;
    }

    if (loadState === "error" && data == null) {
      return <div className={styles.notice}>API unavailable: {message}</div>;
    }

    if (data == null) {
      return null;
    }

    return (
      <>
        <FilterToolbar
          filters={filters}
          projects={data.scopes}
          applications={selectableApplications}
          providers={providerOptions}
          models={modelOptions}
          sourceApps={sourceAppOptions}
          operationTypes={operationOptions}
          errorCategories={errorOptions}
          isRefreshing={loadState === "loading"}
          activeFilterCount={activeFilterCount}
          onChange={updateFilter}
          onReset={() => {
            setSelectedRequest(null);
            setFilters(defaultFilters);
          }}
        />

        {loadState === "error" ? <div className={styles.notice}>Refresh failed: {message}</div> : null}

        <section className={styles.metrics} aria-label="Usage metrics">
          <Metric label="Requests" value={data.summary.request_count.toLocaleString()} />
          <Metric label="Errors" value={data.summary.error_count.toLocaleString()} tone="error" />
          <Metric
            label="Avg latency"
            value={`${Math.round(data.summary.average_latency_ms)} ms`}
          />
          <Metric
            label="Estimated cost"
            value={`$${Number(data.summary.estimated_cost_usd).toFixed(6)}`}
            tone="cost"
          />
        </section>

        <section className={styles.layout}>
          <Panel title="Recent Requests">
            <RequestTable
              rows={data.requests}
              hasFilters={hasFilters}
              kind="requests"
              onSelect={setSelectedRequest}
            />
          </Panel>
          <Panel title="Recent Failures">
            <RequestTable
              rows={data.errors}
              hasFilters={hasFilters}
              kind="failures"
              onSelect={setSelectedRequest}
            />
          </Panel>
          <Panel title="Prompt Versions">
            <ConfigList
              rows={visiblePrompts.map((prompt) => ({
                id: prompt.id,
                primary: prompt.name,
                secondary: `v${prompt.version}`,
                active: prompt.is_active
              }))}
              emptyLabel={hasFilters ? "No prompt versions match the selected scope" : undefined}
            />
          </Panel>
          <Panel title="Model Routes">
            <ConfigList
              rows={visibleRoutes.map((route) => ({
                id: route.id,
                primary: route.model_name,
                secondary: `${route.environment} / ${route.provider} / p${route.priority}`,
                active: route.is_active && route.is_default
              }))}
              emptyLabel={hasFilters ? "No model routes match the selected scope" : undefined}
            />
          </Panel>
        </section>

        {selectedRequest ? (
          <RequestDetail request={selectedRequest} onClose={() => setSelectedRequest(null)} />
        ) : null}
      </>
    );
  })();

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>LLMOps Dashboard</p>
          <h1>Production AI Platform</h1>
        </div>
        <div className={styles.endpoint}>{apiBaseUrl ?? "loading"}</div>
      </header>
      {content}
    </main>
  );
}

function FilterToolbar({
  filters,
  projects,
  applications,
  providers,
  models,
  sourceApps,
  operationTypes,
  errorCategories,
  isRefreshing,
  activeFilterCount,
  onChange,
  onReset
}: {
  filters: DashboardFilters;
  projects: ProjectScope[];
  applications: ApplicationScope[];
  providers: string[];
  models: string[];
  sourceApps: string[];
  operationTypes: string[];
  errorCategories: string[];
  isRefreshing: boolean;
  activeFilterCount: number;
  onChange: (name: keyof DashboardFilters, value: string) => void;
  onReset: () => void;
}) {
  const handleChange =
    (name: keyof DashboardFilters) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      onChange(name, event.target.value);
    };

  return (
    <section className={styles.filters} aria-label="Dashboard filters">
      <div className={styles.filterHeader}>
        <div>
          <h2>Filters</h2>
          <p>
            {isRefreshing
              ? "Refreshing filtered platform data"
              : "Backend-backed usage view, auto-refreshes every 5 seconds"}
          </p>
        </div>
        <button className={styles.resetButton} type="button" onClick={onReset}>
          Reset{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
        </button>
      </div>

      <div className={styles.filterGrid}>
        <label className={styles.field}>
          <span>Project</span>
          <select value={filters.projectId} onChange={handleChange("projectId")}>
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Application</span>
          <select value={filters.applicationId} onChange={handleChange("applicationId")}>
            <option value="">All apps</option>
            {applications.map((application) => (
              <option key={application.id} value={application.id}>
                {application.name} ({application.environment})
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Date range</span>
          <select value={filters.datePreset} onChange={handleChange("datePreset")}>
            <option value="all">All time</option>
            <option value="1h">Last hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="custom">Custom</option>
          </select>
        </label>

        <label className={styles.field}>
          <span>Status</span>
          <select value={filters.status} onChange={handleChange("status")}>
            <option value="">All statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
          </select>
        </label>

        <label className={styles.field}>
          <span>Provider</span>
          <select value={filters.provider} onChange={handleChange("provider")}>
            <option value="">All providers</option>
            {providers.map((provider) => (
              <option key={provider} value={provider}>
                {provider}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Model</span>
          <select value={filters.modelName} onChange={handleChange("modelName")}>
            <option value="">All models</option>
            {models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Source app</span>
          <select value={filters.sourceApp} onChange={handleChange("sourceApp")}>
            <option value="">All sources</option>
            {sourceApps.map((sourceApp) => (
              <option key={sourceApp} value={sourceApp}>
                {sourceApp}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Operation</span>
          <select value={filters.operationType} onChange={handleChange("operationType")}>
            <option value="">All operations</option>
            {operationTypes.map((operationType) => (
              <option key={operationType} value={operationType}>
                {formatOperation(operationType)}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span>Failure category</span>
          <select value={filters.errorCategory} onChange={handleChange("errorCategory")}>
            <option value="">All categories</option>
            {errorCategories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
      </div>

      {filters.datePreset === "custom" ? (
        <div className={styles.customDates}>
          <label className={styles.field}>
            <span>Start</span>
            <input
              type="datetime-local"
              value={filters.createdFrom}
              onChange={handleChange("createdFrom")}
            />
          </label>
          <label className={styles.field}>
            <span>End</span>
            <input
              type="datetime-local"
              value={filters.createdTo}
              onChange={handleChange("createdTo")}
            />
          </label>
        </div>
      ) : null}
    </section>
  );
}

function Metric({
  label,
  value,
  tone = "default"
}: {
  label: string;
  value: string;
  tone?: "default" | "error" | "cost";
}) {
  return (
    <article className={styles.metric} data-tone={tone}>
      <div className={styles.metricLabel}>{label}</div>
      <div className={styles.metricValue}>{value}</div>
    </article>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.panel}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function RequestTable({
  rows,
  hasFilters,
  kind,
  onSelect
}: {
  rows: GatewayRequest[];
  hasFilters: boolean;
  kind: "requests" | "failures";
  onSelect: (request: GatewayRequest) => void;
}) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title={hasFilters ? `No matching ${kind}` : `No ${kind} recorded`}
        description={
          hasFilters
            ? "Reset filters or widen the date range to inspect more gateway or telemetry traffic."
            : "Send a local gateway request or external telemetry event to populate this operational view."
        }
      />
    );
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Request</th>
            <th>Status</th>
            <th>Scope</th>
            <th>Source</th>
            <th>Operation</th>
            <th>Model</th>
            <th>Latency</th>
            <th>Cost</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.request_id}>
              <td title={row.request_id}>
                <button className={styles.requestButton} type="button" onClick={() => onSelect(row)}>
                  {row.request_id.slice(0, 12)}
                </button>
              </td>
              <td>
                <span className={styles.status} data-status={row.status}>
                  {row.error_category ?? row.status}
                </span>
              </td>
              <td>{formatScope(row)}</td>
              <td>{row.source_app ?? "gateway"}</td>
              <td>{row.operation_type == null ? "completion" : formatOperation(row.operation_type)}</td>
              <td>{row.model_name ?? "n/a"}</td>
              <td>{row.latency_ms == null ? "n/a" : `${row.latency_ms} ms`}</td>
              <td>{formatCost(row.estimated_cost_usd)}</td>
              <td>{formatTime(row.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfigList({
  rows,
  emptyLabel = "No configuration records"
}: {
  rows: { id: string; primary: string; secondary: string; active: boolean }[];
  emptyLabel?: string;
}) {
  if (rows.length === 0) {
    return <EmptyState title={emptyLabel} description="Configuration will appear here once seeded." />;
  }

  return (
    <div className={styles.configList}>
      {rows.slice(0, 8).map((row) => (
        <div className={styles.configRow} key={row.id}>
          <div>
            <strong>{row.primary}</strong>
            <span>{row.secondary}</span>
          </div>
          <span className={styles.badge} data-active={row.active}>
            {row.active ? "active" : "inactive"}
          </span>
        </div>
      ))}
    </div>
  );
}

function RequestDetail({
  request,
  onClose
}: {
  request: GatewayRequest;
  onClose: () => void;
}) {
  return (
    <aside className={styles.detailPanel} aria-label="Request details">
      <div className={styles.detailHeader}>
        <div>
          <p className={styles.kicker}>Request Detail</p>
          <h2>{request.request_id}</h2>
        </div>
        <button className={styles.closeButton} type="button" onClick={onClose} aria-label="Close">
          x
        </button>
      </div>

      {request.source_app ? (
        <p className={styles.detailNote}>
          Telemetry reported by {request.source_app}. This platform records usage, latency,
          tokens, cost, and errors; the source app owns product behavior.
        </p>
      ) : null}

      <div className={styles.detailGrid}>
        <DetailRow label="Timestamp" value={formatDateTime(request.created_at)} />
        <DetailRow label="Project" value={request.project_name ?? request.project_id} />
        <DetailRow label="Application" value={formatApplication(request)} />
        <DetailRow label="Source app" value={request.source_app ?? "gateway"} />
        <DetailRow
          label="Operation"
          value={request.operation_type == null ? "completion" : formatOperation(request.operation_type)}
        />
        <DetailRow label="Status" value={request.error_category ?? request.status} />
        <DetailRow label="Provider" value={request.provider ?? "n/a"} />
        <DetailRow label="Model" value={request.model_name ?? "n/a"} />
        <DetailRow label="Latency" value={request.latency_ms == null ? "n/a" : `${request.latency_ms} ms`} />
        <DetailRow
          label="Tokens"
          value={
            request.estimated_input_tokens == null && request.estimated_output_tokens == null
              ? "n/a"
              : `${request.estimated_input_tokens ?? 0} in / ${request.estimated_output_tokens ?? 0} out`
          }
        />
        <DetailRow label="Cost" value={formatCost(request.estimated_cost_usd)} />
        <CopyableId label="Request ID" value={request.request_id} />
        <CopyableId label="External Event ID" value={request.external_event_id ?? "n/a"} />
        <CopyableId label="External Request ID" value={request.external_request_id ?? "n/a"} />
        <CopyableId label="Project ID" value={request.project_id} />
        <CopyableId label="Application ID" value={request.application_id} />
        <CopyableId label="Prompt Version ID" value={request.prompt_version_id ?? "n/a"} />
        <CopyableId label="Model Route ID" value={request.model_route_id ?? "n/a"} />
      </div>
    </aside>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.detailRow}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function CopyableId({ label, value }: { label: string; value: string }) {
  function copy() {
    if (value === "n/a") {
      return;
    }
    void navigator.clipboard?.writeText(value);
  }

  return (
    <div className={styles.detailRow}>
      <dt>{label}</dt>
      <dd>
        <code>{value}</code>
        {value !== "n/a" ? (
          <button className={styles.copyButton} type="button" onClick={copy}>
            Copy
          </button>
        ) : null}
      </dd>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className={styles.empty}>
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

function buildFilterQuery(filters: DashboardFilters) {
  const params = new URLSearchParams();
  appendParam(params, "project_id", filters.projectId);
  appendParam(params, "application_id", filters.applicationId);
  appendParam(params, "status", filters.status);
  appendParam(params, "provider", filters.provider);
  appendParam(params, "model_name", filters.modelName);
  appendParam(params, "source_app", filters.sourceApp);
  appendParam(params, "operation_type", filters.operationType);
  appendParam(params, "error_category", filters.errorCategory);

  const dateRange = resolveDateRange(filters);
  appendParam(params, "created_from", dateRange.createdFrom);
  appendParam(params, "created_to", dateRange.createdTo);

  return params;
}

function buildPath(path: string, params: URLSearchParams, extra: Record<string, string> = {}) {
  const next = new URLSearchParams(params);
  Object.entries(extra).forEach(([key, value]) => next.set(key, value));
  const query = next.toString();
  return query ? `${path}?${query}` : path;
}

function resolveDateRange(filters: DashboardFilters) {
  if (filters.datePreset === "all") {
    return { createdFrom: "", createdTo: "" };
  }

  if (filters.datePreset === "custom") {
    return {
      createdFrom: toIsoFromDateTimeLocal(filters.createdFrom),
      createdTo: toIsoFromDateTimeLocal(filters.createdTo)
    };
  }

  const now = new Date();
  const from = new Date(now);
  const hoursByPreset: Record<Exclude<DatePreset, "all" | "custom">, number> = {
    "1h": 1,
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30
  };
  from.setHours(from.getHours() - hoursByPreset[filters.datePreset]);

  return {
    createdFrom: from.toISOString(),
    createdTo: now.toISOString()
  };
}

function appendParam(params: URLSearchParams, name: string, value: string) {
  if (value.trim() !== "") {
    params.set(name, value);
  }
}

function toIsoFromDateTimeLocal(value: string) {
  if (value.trim() === "") {
    return "";
  }
  return new Date(value).toISOString();
}

function countActiveFilters(filters: DashboardFilters) {
  return [
    filters.projectId,
    filters.applicationId,
    filters.status,
    filters.provider,
    filters.modelName,
    filters.sourceApp,
    filters.operationType,
    filters.errorCategory,
    filters.datePreset === "all" ? "" : filters.datePreset,
    filters.createdFrom,
    filters.createdTo
  ].filter(Boolean).length;
}

function uniqueSorted(values: string[]) {
  return Array.from(new Set(values.filter((value) => value.trim() !== ""))).sort((a, b) =>
    a.localeCompare(b)
  );
}

function filterConfigRows<T extends { project_id: string; application_id: string }>(
  rows: T[],
  filters: DashboardFilters
) {
  return rows.filter((row) => {
    if (filters.projectId && row.project_id !== filters.projectId) {
      return false;
    }
    if (filters.applicationId && row.application_id !== filters.applicationId) {
      return false;
    }
    return true;
  });
}

function formatScope(row: GatewayRequest) {
  const project = row.project_name ?? row.project_slug ?? "unknown project";
  const application = row.application_name ?? row.application_slug ?? "unknown app";
  return `${project} / ${application}`;
}

function formatApplication(row: GatewayRequest) {
  const label = row.application_name ?? row.application_id;
  return row.application_environment ? `${label} (${row.application_environment})` : label;
}

function formatCost(value: string | null) {
  return value == null ? "n/a" : `$${Number(value).toFixed(6)}`;
}

function formatOperation(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
