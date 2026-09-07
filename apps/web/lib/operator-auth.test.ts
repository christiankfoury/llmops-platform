// @vitest-environment node
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { NextRequest } from "next/server";
import { authConfig, cookieName, seal, unseal, randomToken, requireCsrf, session, type AuthConfig } from "./operator-session";
import { proxy } from "./operator-proxy";
import { currentSession, logout } from "./operator-auth-routes";
import { GET as runtimeConfig } from "../app/api/runtime-config/route";

let config: AuthConfig;
beforeEach(() => {
  vi.stubEnv("WEB_AUTH_MODE", "oidc"); vi.stubEnv("ENVIRONMENT", "test");
  vi.stubEnv("WEB_ORIGIN", "http://localhost:3000"); vi.stubEnv("OIDC_ISSUER", "https://identity.fixture.invalid");
  vi.stubEnv("OIDC_AUDIENCE", "https://api.fixture.invalid"); vi.stubEnv("OIDC_CLIENT_ID", "fixture-client");
  vi.stubEnv("WEB_SESSION_SECRET", randomToken()); vi.stubEnv("API_BASE_URL", "http://api.internal:8080");
  config = authConfig();
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });
async function browserRequest(path = "/api/platform/v1/usage/summary", method = "GET", extra: Record<string,string> = {}, body?: string) {
  const token = await seal(config, "session", { accessToken: "synthetic-access-token", csrf: "synthetic-csrf" }, 300);
  return new NextRequest(`${config.origin}${path}`, { method, headers: { Cookie: `${cookieName(config, "session")}=${token}`, ...extra }, body });
}
test("encrypted sessions bind purpose, origin, expiry, and key; tokens are unreadable in cookie values", async () => {
  const token = await seal(config, "session", { accessToken: "private-synthetic-access-token", csrf: randomToken() }, 300);
  expect(token).not.toContain("private-synthetic-access-token");
  expect((await unseal(config, "session", token)).accessToken).toBe("private-synthetic-access-token");
  await expect(unseal(config, "flow", token)).rejects.toThrow();
  await expect(unseal({ ...config, origin: "https://different.invalid" }, "session", token)).rejects.toThrow();
  await expect(unseal({ ...config, secret: Buffer.from(randomToken(), "base64url") }, "session", token)).rejects.toThrow();
  await expect(unseal(config, "session", token.slice(0,-2) + "xx")).rejects.toThrow();
  vi.useFakeTimers(); vi.setSystemTime(Date.now() + 301000);
  try { await expect(unseal(config, "session", token)).rejects.toThrow(); } finally { vi.useRealTimers(); }
});
test("production rejects HTTP identity and malformed session secrets", () => {
  expect(() => authConfig({ ...process.env, ENVIRONMENT: "prod", WEB_ORIGIN: "http://localhost:3000" })).toThrow();
  expect(() => authConfig({ ...process.env, WEB_SESSION_SECRET: "short" })).toThrow();
  expect(() => authConfig({ ...process.env, OIDC_ISSUER: "https://identity.invalid/?redirect=attacker" })).toThrow();
});
test("proxy requires a session and strips caller credentials, cookies, actor headers and upstream cookies", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('{"request_count":0}', { headers: { "Content-Type": "application/json", "Set-Cookie": "attacker=value" } }));
  vi.stubGlobal("fetch", fetcher);
  expect((await proxy(new NextRequest(`${config.origin}/api/platform/v1/usage/summary`), ["v1","usage","summary"])).status).toBe(401);
  expect(fetcher).not.toHaveBeenCalled();
  const response = await proxy(await browserRequest(undefined, "GET", { Authorization: "Bearer attacker", "X-API-Key": "attacker", "X-Actor-ID": "admin" }), ["v1","usage","summary"]);
  expect(response.status).toBe(200); expect(response.headers.get("set-cookie")).toBeNull();
  const [url, options] = fetcher.mock.calls[0];
  expect(url).toBe("http://api.internal:8080/v1/usage/summary");
  expect(options.headers).toEqual({ Authorization: "Bearer synthetic-access-token", Accept: "application/json" });
  expect(options.redirect).toBe("error");
});
test("mutations need matching Origin and CSRF token; logout clears protected cookies", async () => {
  const good = await browserRequest("/api/auth/logout", "POST", { Origin: config.origin, "X-CSRF-Token": "synthetic-csrf" });
  expect(() => requireCsrf(good, config, { accessToken: "x", csrf: "synthetic-csrf", exp: 1 })).not.toThrow();
  const missing = await browserRequest("/api/auth/logout", "POST");
  expect((await logout(missing)).status).toBe(403);
  const cross = await browserRequest("/api/auth/logout", "POST", { Origin: "https://attacker.invalid", "X-CSRF-Token": "synthetic-csrf" });
  expect((await logout(cross)).status).toBe(403);
  const response = await logout(good);
  expect(response.status).toBe(200); expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
  expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  expect(response.headers.get("set-cookie")).toContain("SameSite=lax");
});
test("proxy refuses path escapes, machine routes, unbounded bodies and unauthenticated mutations", async () => {
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  for (const parts of [["https:","attacker.invalid"], ["v1","..","gateway","completions"], ["v1","gateway","completions"], ["v1","operator","me"]]) {
    expect((await proxy(await browserRequest(), parts)).status).toBe(404);
  }
  const path = ["v1","admin","prompt-versions"];
  expect((await proxy(await browserRequest(undefined, "POST", { "Content-Type": "application/json" }, "{}"), path)).status).toBe(403);
  const large = await browserRequest(undefined, "POST", { "Content-Type": "application/json", Origin: config.origin, "X-CSRF-Token": "synthetic-csrf" }, "x".repeat(262145));
  expect((await proxy(large, path)).status).toBe(413);
  expect(fetcher).not.toHaveBeenCalled();
});
test("synthetic demo has fixed read-only data and never connects to identity or backend", async () => {
  vi.stubEnv("WEB_AUTH_MODE", "synthetic_demo");
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  const request = new NextRequest("https://demo.fixture.invalid/api/platform/v1/usage/summary");
  const response = await proxy(request, ["v1","usage","summary"]);
  expect(await response.json()).toEqual({ request_count: 1, error_count: 0, average_latency_ms: 120, estimated_cost_usd: "0.000005" });
  expect((await proxy(new NextRequest(request.url, { method: "POST" }), ["v1","admin","prompt-versions"])).status).toBe(403);
  expect((await currentSession(request)).status).toBe(200);
  expect(fetcher).not.toHaveBeenCalled();
});
test("session response and runtime config never reveal tokens or internal backend URLs", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ authenticated: true, actor_id: "oidc:synthetic", projects: [], access_token: "upstream-secret-must-not-forward" }))));
  const response = await currentSession(await browserRequest());
  const text = await response.text();
  expect(text).toContain('"csrf":"synthetic-csrf"');
  expect(text).not.toContain("synthetic-access-token"); expect(text).not.toContain("upstream-secret");
  expect(await runtimeConfig().json()).toEqual({ apiBaseUrl: "/api/platform" });
  expect((await session(await browserRequest(), config)).accessToken).toBe("synthetic-access-token");
});
test("disabled mode fails closed without backend traffic", async () => {
  vi.stubEnv("WEB_AUTH_MODE", "disabled"); const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  expect((await proxy(new NextRequest(`${config.origin}/api/platform/v1/usage/summary`), ["v1","usage","summary"])).status).toBe(401);
  expect(fetcher).not.toHaveBeenCalled();
});
