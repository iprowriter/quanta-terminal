"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamMemo, fetchMemo, type MemoRecord } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import AgentProgress from "./AgentProgress";
import ChatSidebar from "./ChatSidebar";
import { theme } from "@/lib/theme";

interface Props { ticker: string; }

type Status = "idle" | "loading_cached" | "streaming" | "done" | "error";

export default function MemoViewer({ ticker }: Props) {
  const { user, accessToken } = useAuth();

  const [status,    setStatus]    = useState<Status>("idle");
  const [memo,      setMemo]      = useState<MemoRecord | null>(null);
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [errorMsg,  setErrorMsg]  = useState("");
  const [chatOpen,  setChatOpen]  = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  // On mount: check for a cached memo
  useEffect(() => {
    setStatus("loading_cached");
    fetchMemo(ticker)
      .then((record) => {
        if (record) {
          setMemo(record);
          setCompleted(new Set(["sec","earnings","analyst","news","tech","memo_writer"]));
          setStatus("done");
        } else {
          setStatus("idle");
        }
      })
      .catch(() => setStatus("idle"));
  }, [ticker]);

  function startGeneration() {
    if (!accessToken) return;
    setStatus("streaming");
    setCompleted(new Set());
    setMemo(null);
    setErrorMsg("");

    abortRef.current = streamMemo(
      ticker,
      accessToken,
      (event) => {
        if (event.event === "agent_complete") {
          setCompleted((prev) => new Set([...prev, event.agent as string]));
        } else if (event.event === "memo_complete") {
          setMemo({
            id:                "",
            ticker:            event.ticker as string,
            memo:              event.memo as string,
            date:              event.date as string,
            sec_analysis:      event.sec_analysis as string,
            earnings_analysis: event.earnings_analysis as string,
            analyst_analysis:  event.analyst_analysis as string,
            news_analysis:     event.news_analysis as string,
            tech_analysis:     event.tech_analysis as string,
            generated_by:      user?.id ?? null,
            created_at:        new Date().toISOString(),
          });
          setCompleted(new Set(["sec","earnings","analyst","news","tech","memo_writer"]));
        } else if (event.event === "error") {
          setErrorMsg(event.message as string);
          setStatus("error");
        }
      },
      () => setStatus((s) => s === "streaming" ? "done" : s),
      (msg) => { setErrorMsg(msg); setStatus("error"); },
    );
  }

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const isStreaming = status === "streaming";
  const isDone      = status === "done" && memo !== null;

  return (
    <div
      style={{
        display: "flex",
        height: "calc(100vh - 56px)",
        overflow: "hidden",
      }}
    >
      {/* Main panel */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "32px 40px",
          minWidth: 0,
        }}
      >
        {/* Back + header */}
        <div style={{ marginBottom: "28px" }}>
          <a
            href="/"
            style={{
              fontFamily: theme.font.mono,
              fontSize: "11px",
              color: theme.colors.textMuted,
              textDecoration: "none",
              letterSpacing: "0.08em",
            }}
          >
            ← WATCHLIST
          </a>
          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: "12px" }}>
            <h1
              style={{
                margin: 0,
                fontFamily: theme.font.mono,
                fontSize: "24px",
                fontWeight: 600,
                color: theme.colors.cyan,
                letterSpacing: "0.06em",
              }}
            >
              {ticker}
            </h1>
            {memo && (
              <span style={{ fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted }}>
                {memo.date}
              </span>
            )}

            <div style={{ marginLeft: "auto", display: "flex", gap: "10px" }}>
              {isDone && (
                <button
                  onClick={() => setChatOpen((o) => !o)}
                  style={{
                    padding: "6px 16px",
                    background: chatOpen ? "rgba(0,212,255,0.1)" : "transparent",
                    border: `1px solid ${theme.colors.cyan}`,
                    borderRadius: theme.radius.sm,
                    color: theme.colors.cyan,
                    fontFamily: theme.font.mono,
                    fontSize: "11px",
                    cursor: "pointer",
                    letterSpacing: "0.06em",
                  }}
                >
                  {chatOpen ? "HIDE CHAT" : "OPEN CHAT"}
                </button>
              )}

              {user ? (
                <button
                  onClick={startGeneration}
                  disabled={isStreaming}
                  style={{
                    padding: "6px 16px",
                    background: isStreaming ? "transparent" : theme.colors.green,
                    border: `1px solid ${isStreaming ? theme.colors.textMuted : theme.colors.green}`,
                    borderRadius: theme.radius.sm,
                    color: isStreaming ? theme.colors.textMuted : "#000",
                    fontFamily: theme.font.mono,
                    fontWeight: 600,
                    fontSize: "11px",
                    cursor: isStreaming ? "not-allowed" : "pointer",
                    letterSpacing: "0.06em",
                  }}
                >
                  {isStreaming ? "GENERATING…" : isDone ? "REGENERATE" : "GENERATE MEMO"}
                </button>
              ) : (
                <span style={{ fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted }}>
                  Sign in to generate
                </span>
              )}
            </div>
          </div>
        </div>

        {/* States */}
        {status === "loading_cached" && (
          <p style={{ fontFamily: theme.font.mono, fontSize: "13px", color: theme.colors.textMuted }}>
            CHECKING CACHE…
          </p>
        )}

        {status === "error" && (
          <div
            style={{
              padding: "20px",
              background: "rgba(255,68,102,0.08)",
              border: `1px solid ${theme.colors.red}`,
              borderRadius: theme.radius.md,
              color: theme.colors.red,
              fontFamily: theme.font.mono,
              fontSize: "13px",
            }}
          >
            ERROR: {errorMsg}
          </div>
        )}

        {(isStreaming || (isDone && memo)) && (
          <AgentProgress completed={completed} active={isStreaming} />
        )}

        {status === "idle" && !memo && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "80px 40px",
              textAlign: "center",
              gap: "16px",
            }}
          >
            <p style={{ color: theme.colors.textMuted, fontFamily: theme.font.mono, fontSize: "13px" }}>
              No memo generated yet for {ticker}.
            </p>
            {user && (
              <button
                onClick={startGeneration}
                style={{
                  padding: "10px 28px",
                  background: theme.colors.green,
                  border: "none",
                  borderRadius: theme.radius.sm,
                  color: "#000",
                  fontFamily: theme.font.mono,
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "pointer",
                  letterSpacing: "0.06em",
                  boxShadow: theme.shadow.glow,
                }}
              >
                GENERATE MEMO →
              </button>
            )}
          </div>
        )}

        {/* Memo markdown */}
        {memo && (
          <div
            style={{
              background: theme.colors.bgPanel,
              border: `1px solid ${theme.colors.border}`,
              borderRadius: theme.radius.md,
              padding: "32px 36px",
              lineHeight: 1.8,
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 style={{ fontFamily: theme.font.mono, color: theme.colors.green, fontSize: "20px", marginTop: "32px", marginBottom: "12px", borderBottom: `1px solid ${theme.colors.border}`, paddingBottom: "8px" }}>{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 style={{ fontFamily: theme.font.mono, color: theme.colors.cyan, fontSize: "16px", marginTop: "28px", marginBottom: "10px" }}>{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 style={{ fontFamily: theme.font.mono, color: theme.colors.textPrimary, fontSize: "14px", marginTop: "20px", marginBottom: "8px" }}>{children}</h3>
                ),
                p: ({ children }) => (
                  <p style={{ margin: "0 0 14px", color: theme.colors.textPrimary, fontSize: "14px" }}>{children}</p>
                ),
                strong: ({ children }) => (
                  <strong style={{ color: theme.colors.textPrimary, fontWeight: 600 }}>{children}</strong>
                ),
                li: ({ children }) => (
                  <li style={{ color: theme.colors.textPrimary, fontSize: "14px", marginBottom: "4px" }}>{children}</li>
                ),
                ul: ({ children }) => (
                  <ul style={{ paddingLeft: "20px", marginBottom: "14px" }}>{children}</ul>
                ),
                hr: () => (
                  <hr style={{ border: "none", borderTop: `1px solid ${theme.colors.border}`, margin: "24px 0" }} />
                ),
                code: ({ children }) => (
                  <code style={{ fontFamily: theme.font.mono, background: theme.colors.bg, padding: "2px 6px", borderRadius: "3px", fontSize: "12px", color: theme.colors.cyan }}>{children}</code>
                ),
              }}
            >
              {memo.memo}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* Chat sidebar */}
      {chatOpen && isDone && accessToken && (
        <div style={{ width: "360px", flexShrink: 0 }}>
          <ChatSidebar ticker={ticker} accessToken={accessToken} />
        </div>
      )}
    </div>
  );
}
