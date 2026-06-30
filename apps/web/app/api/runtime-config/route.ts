import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  const apiBaseUrl = (
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");

  return NextResponse.json({ apiBaseUrl });
}
