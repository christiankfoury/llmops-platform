"use client";

import { useEffect, useState } from "react";
import styles from "./health-panel.module.css";

type ApiHealth =
  | {
      state: "loading";
      message: string;
    }
  | {
      state: "ready";
      message: string;
      service: string;
    }
  | {
      state: "error";
      message: string;
    };

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export function HealthPanel() {
  const [health, setHealth] = useState<ApiHealth>({
    state: "loading",
    message: "Checking API health..."
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal
        });

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const payload = (await response.json()) as {
          service?: string;
          status?: string;
        };

        setHealth({
          state: "ready",
          message: payload.status ?? "ok",
          service: payload.service ?? "api"
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setHealth({
          state: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to reach the API health endpoint"
        });
      }
    }

    loadHealth();

    return () => controller.abort();
  }, []);

  return (
    <aside className={styles.panel} aria-label="API health status">
      <div className={styles.header}>
        <span className={styles.statusDot} data-state={health.state} />
        <span className={styles.statusText}>
          {health.state === "ready" ? "API online" : "API status"}
        </span>
      </div>
      <dl className={styles.details}>
        <div>
          <dt>Endpoint</dt>
          <dd>{apiBaseUrl}/health</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{health.message}</dd>
        </div>
        {"service" in health ? (
          <div>
            <dt>Service</dt>
            <dd>{health.service}</dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}
