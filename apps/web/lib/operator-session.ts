import "server-only";
import { randomBytes, timingSafeEqual } from "node:crypto";
import { EncryptJWT, jwtDecrypt, type JWTPayload } from "jose";
import { NextRequest, NextResponse } from "next/server";

export type AuthConfig = {
  mode: "disabled" | "oidc" | "synthetic_demo";
  origin: string;
  issuer: string;
  audience: string;
  clientId: string;
  clientSecret?: string;
  secret: Uint8Array;
  apiBaseUrl: string;
};
export class AuthFailure extends Error {
  constructor(public status: number) { super("Operator access unavailable"); }
}

function required(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name];
  if (!value || value.length > 2048) throw new AuthFailure(503);
  return value;
}
function endpoint(value: string, local: boolean, originOnly = false): URL {
  const url = new URL(value);
  if (url.username || url.password || url.search || url.hash ||
      !(url.protocol === "https:" || local && url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) ||
      originOnly && url.pathname !== "/") throw new AuthFailure(503);
  return url;
}
export function authConfig(env: NodeJS.ProcessEnv = process.env): AuthConfig {
  const mode = env.WEB_AUTH_MODE ?? "disabled";
  if (!["disabled", "oidc", "synthetic_demo"].includes(mode)) throw new AuthFailure(503);
  const empty = { origin: "", issuer: "", audience: "", clientId: "", secret: new Uint8Array(), apiBaseUrl: "" };
  if (mode !== "oidc") return { ...empty, mode: mode as "disabled" | "synthetic_demo" };
  const local = ["local", "test"].includes(env.ENVIRONMENT ?? "local");
  const origin = endpoint(required(env, "WEB_ORIGIN"), local, true).origin;
  const issuer = required(env, "OIDC_ISSUER"); endpoint(issuer, local);
  const audience = required(env, "OIDC_AUDIENCE"); endpoint(audience, local);
  const secretText = required(env, "WEB_SESSION_SECRET");
  const secret = Buffer.from(secretText, "base64url");
  if (secret.length !== 32 || secret.toString("base64url") !== secretText) throw new AuthFailure(503);
  const api = new URL(required(env, "API_BASE_URL"));
  // Internal service HTTP is supported; transport/network policy is configured at runtime cutover.
  if (!["https:", "http:"].includes(api.protocol) || api.username || api.password || api.search || api.hash || api.pathname !== "/") throw new AuthFailure(503);
  return { mode, origin, issuer, audience, clientId: required(env, "OIDC_CLIENT_ID"),
    clientSecret: env.OIDC_CLIENT_SECRET || undefined, secret, apiBaseUrl: api.origin };
}
export function cookieName(config: AuthConfig, purpose: "session" | "flow"): string {
  return `${config.origin.startsWith("https:") ? "__Host-" : ""}pap_${purpose}`;
}
export function randomToken(): string { return randomBytes(32).toString("base64url"); }
export async function seal(config: AuthConfig, purpose: "session" | "flow", payload: JWTPayload, seconds: number): Promise<string> {
  if (seconds < 1 || seconds > 900) throw new AuthFailure(401);
  const value = await new EncryptJWT(payload).setProtectedHeader({ alg: "dir", enc: "A256GCM" })
    .setIssuer(config.origin).setAudience(`pap:${purpose}`).setIssuedAt().setExpirationTime(Math.floor(Date.now()/1000) + seconds)
    .encrypt(config.secret);
  if (value.length > 3600) throw new AuthFailure(502);
  return value;
}
export async function unseal(config: AuthConfig, purpose: "session" | "flow", value: string | undefined): Promise<JWTPayload> {
  if (!value || value.length > 3600) throw new AuthFailure(401);
  try {
    const { payload } = await jwtDecrypt(value, config.secret, {
      issuer: config.origin, audience: `pap:${purpose}`, clockTolerance: 0,
      keyManagementAlgorithms: ["dir"], contentEncryptionAlgorithms: ["A256GCM"], requiredClaims: ["exp", "iat"]
    });
    return payload;
  } catch { throw new AuthFailure(401); }
}
export function setCookie(response: NextResponse, config: AuthConfig, purpose: "session" | "flow", value: string, maxAge: number) {
  response.cookies.set(cookieName(config, purpose), value, {
    httpOnly: true, secure: config.origin.startsWith("https:"), sameSite: "lax", path: "/", maxAge
  });
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
}
export function sameOrigin(request: NextRequest, config: AuthConfig, mutation = false) {
  if (new URL(request.url).origin !== config.origin ||
      mutation && request.headers.get("origin") !== config.origin) throw new AuthFailure(403);
}
export type OperatorSession = { accessToken: string; csrf: string; exp: number };
export async function session(request: NextRequest, config: AuthConfig): Promise<OperatorSession> {
  if (config.mode !== "oidc") throw new AuthFailure(401);
  sameOrigin(request, config);
  const payload = await unseal(config, "session", request.cookies.get(cookieName(config, "session"))?.value);
  if (typeof payload.accessToken !== "string" || typeof payload.csrf !== "string" || typeof payload.exp !== "number") throw new AuthFailure(401);
  return { accessToken: payload.accessToken, csrf: payload.csrf, exp: payload.exp };
}
export function requireCsrf(request: NextRequest, config: AuthConfig, current: OperatorSession) {
  sameOrigin(request, config, true);
  const supplied = request.headers.get("x-csrf-token") ?? "";
  const left = Buffer.from(supplied); const right = Buffer.from(current.csrf);
  if (left.length !== right.length || !timingSafeEqual(left, right)) throw new AuthFailure(403);
}
export function jsonResponse(value: unknown, status = 200) {
  return NextResponse.json(value, { status, headers: { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" } });
}
export function safeFailure(error: unknown) {
  return jsonResponse({ detail: "Operator access unavailable" }, error instanceof AuthFailure ? error.status : 503);
}
export async function boundedBody(request: Pick<Request, "headers" | "body">, maximum: number): Promise<string> {
  const declared = request.headers.get("content-length");
  if (declared && (!/^\d+$/.test(declared) || Number(declared) > maximum)) throw new AuthFailure(413);
  const reader = request.body?.getReader();
  if (!reader) return "";
  const chunks: Uint8Array[] = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > maximum) { await reader.cancel(); throw new AuthFailure(413); }
      chunks.push(value);
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks));
  } finally { reader.releaseLock(); }
}
