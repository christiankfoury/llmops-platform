import "server-only";
import { NextRequest } from "next/server";
import { authConfig, boundedBody, jsonResponse, requireCsrf, safeFailure, session, setCookie } from "./operator-session";

export async function currentSession(request: NextRequest) {
  try {
    const config = authConfig();
    if (config.mode === "synthetic_demo") return jsonResponse({ authenticated: true, mode: "synthetic_demo", projects: [] });
    if (config.mode === "disabled") return jsonResponse({ authenticated: false, mode: "disabled" });
    const current = await session(request, config);
    const check = await fetch(`${config.apiBaseUrl}/v1/operator/me`, { headers: { Authorization: `Bearer ${current.accessToken}` }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
    if (!check.ok) return jsonResponse({ authenticated: false, mode: "oidc" }, check.status === 401 ? 200 : 503);
    const identity = JSON.parse(await boundedBody(check, 262144));
    return jsonResponse({ authenticated: true, mode: "oidc", actorId: identity.actor_id, projects: identity.projects, csrf: current.csrf, expiresAt: current.exp });
  } catch { return jsonResponse({ authenticated: false, mode: "oidc" }); }
}
export async function logout(request: NextRequest) {
  try {
    const config = authConfig(); const current = await session(request, config);
    requireCsrf(request, config, current);
    const response = jsonResponse({ authenticated: false });
    setCookie(response, config, "session", "", 0); setCookie(response, config, "flow", "", 0);
    return response;
  } catch (error) { return safeFailure(error); }
}
