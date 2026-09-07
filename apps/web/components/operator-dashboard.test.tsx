import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { OperatorDashboard } from "./operator-dashboard";
import { syntheticDemo } from "../lib/synthetic-demo";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
test("signed-out users see sign-in without mounting the data dashboard", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ authenticated: false, mode: "oidc" }) });
  vi.stubGlobal("fetch", fetcher); render(<OperatorDashboard />);
  expect(await screen.findByRole("link", { name: "Sign in to the operator dashboard" })).toHaveAttribute("href", "/api/auth/login");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][0]).toBe("/api/auth/session");
});
test("explicit synthetic mode renders the existing dashboard with a clear read-only label", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    const url = new URL(input, "http://localhost:3000");
    let value: unknown;
    if (url.pathname === "/api/auth/session") value = { authenticated: true, mode: "synthetic_demo" };
    else if (url.pathname === "/api/runtime-config") value = { apiBaseUrl: "/api/platform" };
    else value = syntheticDemo(url.pathname.replace("/api/platform/", ""), url.searchParams);
    return { ok: true, json: async () => value };
  }));
  render(<OperatorDashboard />);
  expect(await screen.findByText("Synthetic demo · Fixed example data · Read only")).toBeVisible();
  expect(await screen.findAllByText("$0.000005")).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
});
