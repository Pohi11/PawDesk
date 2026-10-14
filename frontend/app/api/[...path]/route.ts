import type { NextRequest } from "next/server";

import { allowedPath } from "@/lib/proxy";

// Server-only: never bundled for the browser, which reaches the backend only through here.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const notFound = () => Response.json({ detail: "not found" }, { status: 404 });

async function forward(request: NextRequest, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  const target = allowedPath(request.method, path);
  if (target === null) {
    return notFound();
  }

  const headers: Record<string, string> = { accept: request.headers.get("accept") ?? "*/*" };
  let body: string | undefined;
  if (request.method === "POST") {
    headers["content-type"] = "application/json";
    body = await request.text();
  }
  const upstream = await fetch(new URL(target + request.nextUrl.search, `${BACKEND_URL}/`), {
    method: request.method,
    headers,
    body,
    cache: "no-store",
    signal: request.signal, // a closed browser tab stops the upstream stream too
  });

  // Pass the body through as a stream, so server-sent events arrive as they are sent.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-cache",
    },
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = notFound;
export const PATCH = notFound;
export const DELETE = notFound;
