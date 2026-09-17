"use client";
import { useEffect, useState } from "react";
import { Dashboard } from "./dashboard";
import styles from "./dashboard.module.css";

type Session = { authenticated: boolean; mode: string; csrf?: string; expiresAt?: number; projects?: { project_id: string; role: string }[] };
export function OperatorDashboard() {
  const [identity, setIdentity] = useState<Session | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Session unavailable");
        const value: Session = await response.json();
        if (controller.signal.aborted) return;
        setIdentity(value); setUnavailable(false);
        timer = setTimeout(load, Math.max(1000, Math.min(30000, ((value.expiresAt ?? Date.now()/1000 + 30) * 1000 - Date.now()))));
      } catch { if (!controller.signal.aborted) { setUnavailable(true); setIdentity(null); } }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  async function signOut() {
    const response = await fetch("/api/auth/logout", { method: "POST", headers: { "X-CSRF-Token": identity?.csrf ?? "" } });
    if (response.ok) { setIdentity({ authenticated: false, mode: "oidc" }); }
    else setUnavailable(true);
  }
  if (unavailable) return <main><h1>Operator dashboard unavailable</h1><p>Reload to retry the connection.</p></main>;
  if (!identity) return <main><p>Checking sign-in…</p></main>;
  if (!identity.authenticated) return <main><h1>Production AI Platform</h1>{identity.mode === "disabled" ?
    <p>Operator sign-in has not been configured.</p> : <a href="/api/auth/login">Sign in to the operator dashboard</a>}</main>;
  return <><aside className={styles.accessNotice} aria-label="Dashboard access">{identity.mode === "synthetic_demo" ?
    <p>Demo mode · Sample data · Read only</p> : <><span>Signed in · Project access controlled by your grants</span> <button onClick={() => void signOut()}>Sign out</button></>}</aside><Dashboard /></>;
}
