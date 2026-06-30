"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import styles from "./dashboard.module.css";

type UsageSummary = {
  request_count: number;
  error_count: number;
  average_latency_ms: number;
  estimated_cost_usd: string;
};

type GatewayRequest = {
  request_id: string;
  status: string;
  provider: string | null;
  model_name: string | null;
  latency_ms: number | null;
  estimated_input_tokens: number | null;
  estimated_output_tokens: number | null;
  estimated_cost_usd: string | null;
  error_category: string | null;
  created_at: string;
};

type PromptVersion = {
  id: string;
  name: string;
  version: number;
  is_active: boolean;
};

type ModelRoute = {
  id: string;
  environment: string;
  provider: string;
  model_name: string;
  priority: number;
  is_default: boolean;
  is_active: boolean;
};

type DashboardState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      apiBaseUrl: string;
      summary: UsageSummary;
      requests: GatewayRequest[];
      errors: GatewayRequest[];
      prompts: PromptVersion[];
      routes: ModelRoute[];
    };

type RuntimeConfig = {
  apiBaseUrl: string;
};

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
  const [state, setState] = useState<DashboardState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard() {
      try {
        const { apiBaseUrl } = await getRuntimeConfig(controller.signal);
        const [summary, requests, errors, prompts, routes] = await Promise.all([
          getJson<UsageSummary>(apiBaseUrl, "/v1/usage/summary", controller.signal),
          getJson<GatewayRequest[]>(
            apiBaseUrl,
            "/v1/usage/requests?limit=12",
            controller.signal
          ),
          getJson<GatewayRequest[]>(
            apiBaseUrl,
            "/v1/usage/errors?limit=8",
            controller.signal
          ),
          getJson<PromptVersion[]>(
            apiBaseUrl,
            "/v1/admin/prompt-versions",
            controller.signal
          ),
          getJson<ModelRoute[]>(apiBaseUrl, "/v1/admin/model-routes", controller.signal)
        ]);

        setState({ status: "ready", apiBaseUrl, summary, requests, errors, prompts, routes });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Dashboard load failed"
        });
      }
    }

    loadDashboard();

    return () => controller.abort();
  }, []);

  const content = useMemo(() => {
    if (state.status === "loading") {
      return <div className={styles.notice}>Loading platform data</div>;
    }

    if (state.status === "error") {
      return <div className={styles.notice}>API unavailable: {state.message}</div>;
    }

    return (
      <>
        <section className={styles.metrics} aria-label="Usage metrics">
          <Metric label="Requests" value={state.summary.request_count.toLocaleString()} />
          <Metric label="Errors" value={state.summary.error_count.toLocaleString()} tone="error" />
          <Metric
            label="Avg latency"
            value={`${Math.round(state.summary.average_latency_ms)} ms`}
          />
          <Metric
            label="Estimated cost"
            value={`$${Number(state.summary.estimated_cost_usd).toFixed(6)}`}
            tone="cost"
          />
        </section>

        <section className={styles.layout}>
          <Panel title="Recent Requests">
            <RequestTable rows={state.requests} />
          </Panel>
          <Panel title="Recent Failures">
            <RequestTable rows={state.errors} emptyLabel="No failures recorded" />
          </Panel>
          <Panel title="Prompt Versions">
            <ConfigList
              rows={state.prompts.map((prompt) => ({
                id: prompt.id,
                primary: prompt.name,
                secondary: `v${prompt.version}`,
                active: prompt.is_active
              }))}
            />
          </Panel>
          <Panel title="Model Routes">
            <ConfigList
              rows={state.routes.map((route) => ({
                id: route.id,
                primary: route.model_name,
                secondary: `${route.environment} / ${route.provider} / p${route.priority}`,
                active: route.is_active && route.is_default
              }))}
            />
          </Panel>
        </section>
      </>
    );
  }, [state]);

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>LLMOps Dashboard</p>
          <h1>Production AI Platform</h1>
        </div>
        <div className={styles.endpoint}>
          {state.status === "ready" ? state.apiBaseUrl : "loading"}
        </div>
      </header>
      {content}
    </main>
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
  emptyLabel = "No requests recorded"
}: {
  rows: GatewayRequest[];
  emptyLabel?: string;
}) {
  if (rows.length === 0) {
    return <div className={styles.empty}>{emptyLabel}</div>;
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Request</th>
            <th>Status</th>
            <th>Model</th>
            <th>Latency</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.request_id}>
              <td title={row.request_id}>{row.request_id.slice(0, 12)}</td>
              <td>
                <span className={styles.status} data-status={row.status}>
                  {row.error_category ?? row.status}
                </span>
              </td>
              <td>{row.model_name ?? "n/a"}</td>
              <td>{row.latency_ms == null ? "n/a" : `${row.latency_ms} ms`}</td>
              <td>
                {row.estimated_cost_usd == null
                  ? "n/a"
                  : `$${Number(row.estimated_cost_usd).toFixed(6)}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfigList({
  rows
}: {
  rows: { id: string; primary: string; secondary: string; active: boolean }[];
}) {
  if (rows.length === 0) {
    return <div className={styles.empty}>No configuration records</div>;
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
