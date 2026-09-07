// @vitest-environment node
import { afterAll, afterEach, beforeAll, beforeEach, expect, test, vi } from "vitest";
import { createServer, type Server } from "node:http";
import { createHash } from "node:crypto";
import { exportJWK, generateKeyPair, SignJWT, jwtVerify } from "jose";
import { NextRequest } from "next/server";
import { login, callback } from "./operator-oidc";
import { authConfig, cookieName, randomToken, session } from "./operator-session";

let server: Server; let issuer: string;
let keys: Awaited<ReturnType<typeof generateKeyPair>>;
let otherKeys: Awaited<ReturnType<typeof generateKeyPair>>;
let tokenRequests = 0;
let invalidSignature = false;
const codes = new Map<string, { nonce: string; challenge: string }>();
beforeAll(async () => {
  keys = await generateKeyPair("RS256"); otherKeys = await generateKeyPair("RS256");
  const publicKey = { ...await exportJWK(keys.publicKey), kid: "fixture", alg: "RS256", use: "sig" };
  server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url!, issuer);
      response.setHeader("Content-Type", "application/json");
      if (url.pathname === "/.well-known/openid-configuration") {
        response.end(JSON.stringify({ issuer, authorization_endpoint: `${issuer}/authorize`, token_endpoint: `${issuer}/token`, jwks_uri: `${issuer}/jwks`,
          response_types_supported: ["code"], subject_types_supported: ["public"], id_token_signing_alg_values_supported: ["RS256"],
          token_endpoint_auth_methods_supported: ["none"], code_challenge_methods_supported: ["S256"] }));
      } else if (url.pathname === "/jwks") response.end(JSON.stringify({ keys: [publicKey] }));
      else if (url.pathname === "/authorize") {
        const code = randomToken();
        if (url.searchParams.get("code_challenge_method") !== "S256" || url.searchParams.get("resource") !== "https://api.fixture.invalid") throw new Error("Expected PKCE and resource audience");
        codes.set(code, { nonce: url.searchParams.get("nonce")!, challenge: url.searchParams.get("code_challenge")! });
        const redirect = new URL(url.searchParams.get("redirect_uri")!);
        redirect.searchParams.set("code", code); redirect.searchParams.set("state", url.searchParams.get("state")!);
        response.writeHead(302, { Location: redirect.href }); response.end();
      } else if (url.pathname === "/token") {
        tokenRequests++;
        let body = ""; for await (const chunk of request) body += chunk;
        const params = new URLSearchParams(body); const code = params.get("code")!;
        const flow = codes.get(code); codes.delete(code);
        if (!flow || createHash("sha256").update(params.get("code_verifier") ?? "").digest("base64url") !== flow.challenge) {
          response.writeHead(400); response.end(JSON.stringify({ error: "invalid_grant" })); return;
        }
        const access = await new SignJWT({ token_use: "access" }).setProtectedHeader({ alg: "RS256", kid: "fixture" })
          .setIssuer(issuer).setSubject("synthetic-operator").setAudience("https://api.fixture.invalid").setIssuedAt().setExpirationTime("5m").sign(keys.privateKey);
        const identity = await new SignJWT({ nonce: flow.nonce }).setProtectedHeader({ alg: "RS256", kid: "fixture" })
          .setIssuer(issuer).setSubject("synthetic-operator").setAudience("fixture-client").setIssuedAt().setExpirationTime("5m")
          .sign(invalidSignature ? otherKeys.privateKey : keys.privateKey);
        response.end(JSON.stringify({ access_token: access, token_type: "Bearer", expires_in: 300, id_token: identity }));
      } else if (url.pathname === "/v1/operator/me") {
        await jwtVerify((request.headers.authorization ?? "").slice(7), keys.publicKey, { issuer, audience: "https://api.fixture.invalid" });
        response.end(JSON.stringify({ authenticated: true, actor_id: "oidc:fixture", projects: [] }));
      } else { response.writeHead(404); response.end("{}"); }
    } catch { response.writeHead(400); response.end(JSON.stringify({ error: "invalid_request" })); }
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address(); if (!address || typeof address === "string") throw new Error("Expected fixture address");
  issuer = `http://127.0.0.1:${address.port}`;
});
afterAll(async () => { server.closeAllConnections(); await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())); });
beforeEach(() => {
  invalidSignature = false; tokenRequests = 0; codes.clear();
  vi.stubEnv("WEB_AUTH_MODE", "oidc"); vi.stubEnv("ENVIRONMENT", "test"); vi.stubEnv("WEB_ORIGIN", "http://localhost:3000");
  vi.stubEnv("OIDC_ISSUER", issuer); vi.stubEnv("OIDC_CLIENT_ID", "fixture-client"); vi.stubEnv("OIDC_CLIENT_SECRET", "");
  vi.stubEnv("OIDC_AUDIENCE", "https://api.fixture.invalid"); vi.stubEnv("API_BASE_URL", issuer); vi.stubEnv("WEB_SESSION_SECRET", randomToken());
});
afterEach(() => vi.unstubAllEnvs());
async function begin() {
  const response = await login(new NextRequest("http://localhost:3000/api/auth/login"));
  expect(response.status).toBe(303);
  const cookie = response.cookies.get(cookieName(authConfig(), "flow"))!;
  expect(cookie.httpOnly).toBe(true); expect(cookie.sameSite).toBe("lax");
  const authorization = await fetch(response.headers.get("location")!, { redirect: "manual" });
  expect(authorization.status).toBe(302);
  return { url: authorization.headers.get("location")!, cookie: `${cookie.name}=${cookie.value}` };
}
test("real local OIDC code exchange verifies PKCE, state, nonce and ID signature before making a session", async () => {
  const flow = await begin();
  const response = await callback(new NextRequest(flow.url, { headers: { Cookie: flow.cookie } }));
  expect(response.status).toBe(303); expect(response.headers.get("location")).toBe("http://localhost:3000/");
  expect(tokenRequests).toBe(1);
  const cookie = response.cookies.get(cookieName(authConfig(), "session"))!;
  const current = await session(new NextRequest("http://localhost:3000/api/auth/session", { headers: { Cookie: `${cookie.name}=${cookie.value}` } }), authConfig());
  expect(current.accessToken.split(".")).toHaveLength(3); expect(current.csrf.length).toBe(43);
  expect(response.cookies.get(cookieName(authConfig(), "flow"))?.maxAge).toBe(0);
  expect((await callback(new NextRequest(flow.url, { headers: { Cookie: flow.cookie } }))).status).toBe(401);
});
test("tampered state and absent flow cookies cannot exchange a code", async () => {
  const flow = await begin(); const url = new URL(flow.url); url.searchParams.set("state", "attacker-state");
  expect((await callback(new NextRequest(url, { headers: { Cookie: flow.cookie } }))).status).toBe(401);
  expect((await callback(new NextRequest(flow.url))).status).toBe(401);
  expect(tokenRequests).toBe(0);
});
test("ID token signature is checked even when the token response comes from the expected server", async () => {
  const flow = await begin(); invalidSignature = true;
  const response = await callback(new NextRequest(flow.url, { headers: { Cookie: flow.cookie } }));
  expect(response.status).toBe(401); expect(tokenRequests).toBe(1);
  expect(response.cookies.get(cookieName(authConfig(), "session"))).toBeUndefined();
});
