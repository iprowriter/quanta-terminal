/**
 * Catch-all proxy route — forwards every /api/* request to the Railway backend.
 *
 * This is more reliable on Vercel than next.config.ts rewrites, because
 * Vercel's edge layer intercepts /api/ paths before rewrites can run.
 *
 * SSE streams (memo generation) are forwarded transparently via ReadableStream.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(request.url);

  // Reconstruct the backend URL preserving query string
  const backendUrl = `${BACKEND_URL}/api/${path.join("/")}${url.search}`;

  // Forward headers but strip host (causes TLS mismatch on Railway)
  const headers = new Headers(request.headers);
  headers.delete("host");

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    // @ts-expect-error — duplex is required for streaming request bodies
    init.duplex = "half";
    init.body = request.body;
  }

  const backendResponse = await fetch(backendUrl, init);

  // Stream the response body straight through (handles SSE + regular JSON)
  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: backendResponse.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;

// Allow streaming responses (SSE) — don't buffer
export const dynamic = "force-dynamic";
