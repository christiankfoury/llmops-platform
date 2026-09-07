import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { authConfig, AuthFailure, boundedBody, jsonResponse, requireCsrf, safeFailure, session } from "./operator-session";
import { syntheticDemo } from "./synthetic-demo";

const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
export function allowedPath(path: string, method: string): boolean {
  if (method === "GET") return /^(v1\/usage\/(summary|requests|errors|scopes)|v1\/admin\/(prompt-versions|model-routes))$/.test(path) ||
    new RegExp(`^v1/admin/applications/${id}/api-keys$`).test(path);
  if (method === "POST") return /^v1\/admin\/(prompt-versions|model-routes)$/.test(path) ||
    new RegExp(`^v1/admin/(applications/${id}/api-keys|api-keys/${id}/revoke|(prompt-versions|model-routes)/${id}/activate)$`).test(path);
  return method === "PATCH" && new RegExp(`^v1/admin/(prompt-versions|model-routes)/${id}$`).test(path);
}
export async function proxy(request: NextRequest, pathParts: string[]) {
  try {
    const config = authConfig();
    const path = pathParts.join("/");
    if (!allowedPath(path, request.method) || request.nextUrl.search.length > 4096) throw new AuthFailure(404);
    if (config.mode === "synthetic_demo") {
      if (request.method !== "GET") throw new AuthFailure(403);
      const value = syntheticDemo(path, request.nextUrl.searchParams);
      if (value === undefined) throw new AuthFailure(404);
      return jsonResponse(value);
    }
    const current = await session(request, config);
    let body: string | undefined;
    if (request.method !== "GET") {
      requireCsrf(request, config, current);
      if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") throw new AuthFailure(415);
      body = await boundedBody(request, 262144);
    }
    const upstream = await fetch(`${config.apiBaseUrl}/${path}${request.nextUrl.search}`, {
      method: request.method, body, headers: { Authorization: `Bearer ${current.accessToken}`, Accept: "application/json", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000)
    });
    if (!upstream.headers.get("content-type")?.startsWith("application/json")) throw new AuthFailure(502);
    const text = await boundedBody(upstream, 2 * 1024 * 1024);
    JSON.parse(text);
    return new NextResponse(text, { status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" } });
  } catch (error) { return safeFailure(error); }
}
