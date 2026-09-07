import "server-only";
import * as oidc from "openid-client";
import { NextRequest, NextResponse } from "next/server";
import { AuthFailure, authConfig, cookieName, jsonResponse, randomToken, safeFailure, sameOrigin, seal, setCookie, unseal, type AuthConfig } from "./operator-session";

let discovery: { key: string; value: Promise<oidc.Configuration>; until: number } | undefined;
async function client(config: AuthConfig) {
  const key = JSON.stringify([config.issuer, config.clientId, config.clientSecret]);
  if (!discovery || discovery.key !== key || discovery.until < Date.now()) {
    discovery = { key, until: Date.now() + 300_000, value: oidc.discovery(new URL(config.issuer), config.clientId,
      config.clientSecret, undefined, { timeout: 5,
        execute: config.issuer.startsWith("http:") ? [oidc.allowInsecureRequests] : undefined
      }).then(value => { oidc.enableNonRepudiationChecks(value); return value; }) };
  }
  return discovery.value;
}
export async function login(request: NextRequest) {
  try {
    const config = authConfig();
    if (config.mode !== "oidc") throw new AuthFailure(503);
    sameOrigin(request, config);
    const provider = await client(config);
    const verifier = oidc.randomPKCECodeVerifier();
    const state = oidc.randomState(); const nonce = oidc.randomNonce();
    const url = oidc.buildAuthorizationUrl(provider, {
      redirect_uri: `${config.origin}/api/auth/callback`, scope: "openid", response_type: "code",
      code_challenge: await oidc.calculatePKCECodeChallenge(verifier), code_challenge_method: "S256",
      state, nonce, resource: config.audience
    });
    const response = NextResponse.redirect(url, 303);
    setCookie(response, config, "flow", await seal(config, "flow", { verifier, state, nonce }, 300), 300);
    return response;
  } catch (error) { return safeFailure(error); }
}
export async function callback(request: NextRequest) {
  let config: AuthConfig | undefined;
  let response: NextResponse;
  try {
    config = authConfig();
    if (config.mode !== "oidc") throw new AuthFailure(503);
    sameOrigin(request, config);
    if (request.url.length > 8192) throw new AuthFailure(400);
    const flow = await unseal(config, "flow", request.cookies.get(cookieName(config, "flow"))?.value);
    if (typeof flow.verifier !== "string" || typeof flow.state !== "string" || typeof flow.nonce !== "string") throw new AuthFailure(401);
    const tokens = await oidc.authorizationCodeGrant(await client(config), new URL(request.url), {
      pkceCodeVerifier: flow.verifier, expectedState: flow.state, expectedNonce: flow.nonce, idTokenExpected: true
    }, { resource: config.audience });
    if (!tokens.access_token || tokens.token_type.toLowerCase() !== "bearer" || !tokens.expires_in || !Number.isFinite(tokens.expires_in)) throw new AuthFailure(401);
    // API verification binds issuer, signature, audience, expiry and server-side project grants.
    const check = await fetch(`${config.apiBaseUrl}/v1/operator/me`, { headers: { Authorization: `Bearer ${tokens.access_token}` },
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
    if (!check.ok) throw new AuthFailure(401);
    await check.body?.cancel();
    const seconds = Math.min(900, Math.floor(tokens.expires_in));
    response = NextResponse.redirect(`${config.origin}/`, 303);
    setCookie(response, config, "session", await seal(config, "session", { accessToken: tokens.access_token, csrf: randomToken() }, seconds), seconds);
  } catch { response = jsonResponse({ detail: "Sign-in failed. Start a new sign-in attempt." }, 401); }
  if (config?.mode === "oidc") setCookie(response, config, "flow", "", 0);
  return response;
}
