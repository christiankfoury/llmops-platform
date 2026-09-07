import { NextRequest } from "next/server";
import { proxy } from "../../../../lib/operator-proxy";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
export { handle as GET, handle as POST, handle as PATCH };
