/**
 * API client — thin wrappers around the FastAPI backend.
 * Base URL is proxied via next.config.ts rewrites (/api → localhost:8000/api).
 */

// In production, call Railway directly (Vercel blocks server-side proxy to Railway).
// NEXT_PUBLIC_API_URL = https://quanta-terminal-production.up.railway.app/api/v1
// Falls back to relative URL for local dev (proxied via next.config.ts).
const BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface StockQuote {
  ticker:     string;
  name:       string;
  price:      number | null;
  change_pct: number | null;
  market_cap: number | null;
  volume:     number | null;
}

export interface MemoRecord {
  id:                string;
  ticker:            string;
  memo:              string;
  date:              string;
  sec_analysis:      string;
  earnings_analysis: string;
  analyst_analysis:  string;
  news_analysis:     string;
  tech_analysis:     string;
  generated_by:      string | null;
  created_at:        string;
}

export type AgentName = "analyst" | "earnings" | "sec" | "news" | "tech";

export interface ChatResponse {
  text:      string;
  thread_id: string;
  agent:     AgentName;
}

// ---------------------------------------------------------------------------
// Stocks
// ---------------------------------------------------------------------------

export async function fetchStocks(): Promise<StockQuote[]> {
  const res = await fetch(`${BASE}/stocks`, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error("Failed to fetch stocks");
  const data = await res.json();
  return data.stocks;
}

// ---------------------------------------------------------------------------
// Memos
// ---------------------------------------------------------------------------

export async function fetchMemo(ticker: string): Promise<MemoRecord | null> {
  const res = await fetch(`${BASE}/memo/${ticker}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch memo");
  return res.json();
}

/**
 * Opens a fetch-based SSE stream for memo generation.
 * Calls onEvent for each parsed event, onDone when the stream closes.
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamMemo(
  ticker: string,
  token: string,
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE}/memo/${ticker}/generate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
        },
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        onError(body.detail ?? `HTTP ${res.status}`);
        onDone();
        return;
      }

      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              onEvent(event);
            } catch { /* malformed line — skip */ }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError(err.message);
      }
    } finally {
      onDone();
    }
  })();

  return controller;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendChat(
  ticker: string,
  message: string,
  agent: AgentName,
  threadId: string | null,
  token: string,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ ticker, message, agent, thread_id: threadId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Chat request failed");
  }
  return res.json();
}
