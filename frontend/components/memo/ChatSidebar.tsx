"use client";

import { useState, useRef, useEffect } from "react";
import { sendChat, type AgentName } from "@/lib/api";
import { theme } from "@/lib/theme";

const AGENTS: { value: AgentName; label: string }[] = [
  { value: "analyst",  label: "Analyst" },
  { value: "earnings", label: "Earnings" },
  { value: "sec",      label: "SEC" },
  { value: "news",     label: "News" },
  { value: "tech",     label: "Tech" },
];

interface Message {
  role:  "user" | "assistant";
  text:  string;
  agent: AgentName;
}

interface Props {
  ticker:      string;
  accessToken: string;
}

export default function ChatSidebar({ ticker, accessToken }: Props) {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [agent,     setAgent]     = useState<AgentName>("analyst");
  const [threadId,  setThreadId]  = useState<string | null>(null);
  const [loading,   setLoading]   = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((m) => [...m, { role: "user", text, agent }]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(ticker, text, agent, threadId, accessToken);
      setThreadId(res.thread_id);
      setMessages((m) => [...m, { role: "assistant", text: res.text, agent: res.agent }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${msg}`, agent }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: theme.colors.bgPanel,
        borderLeft: `1px solid ${theme.colors.border}`,
      }}
    >
      {/* Sidebar header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: `1px solid ${theme.colors.border}`,
          flexShrink: 0,
        }}
      >
        <p style={{ margin: 0, fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted, letterSpacing: "0.1em" }}>
          CHAT WITH SPECIALIST
        </p>

        {/* Agent selector */}
        <div style={{ display: "flex", gap: "6px", marginTop: "10px", flexWrap: "wrap" }}>
          {AGENTS.map((a) => (
            <button
              key={a.value}
              onClick={() => setAgent(a.value)}
              style={{
                padding: "4px 10px",
                background: agent === a.value ? "rgba(0,255,136,0.12)" : "transparent",
                border: `1px solid ${agent === a.value ? theme.colors.green : theme.colors.border}`,
                borderRadius: theme.radius.sm,
                color: agent === a.value ? theme.colors.green : theme.colors.textSecondary,
                fontFamily: theme.font.mono,
                fontSize: "10px",
                cursor: "pointer",
                letterSpacing: "0.06em",
              }}
            >
              {a.label.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Message list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.length === 0 && (
          <p style={{ color: theme.colors.textMuted, fontFamily: theme.font.mono, fontSize: "12px", lineHeight: 1.6 }}>
            Ask any question about {ticker}.<br />
            Select a specialist above to route your query.
          </p>
        )}

        {messages.map((m, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <span
              style={{
                fontFamily: theme.font.mono,
                fontSize: "10px",
                color: m.role === "user" ? theme.colors.cyan : theme.colors.green,
                letterSpacing: "0.06em",
              }}
            >
              {m.role === "user" ? "YOU" : `${m.agent.toUpperCase()} AGENT`}
            </span>
            <p
              style={{
                margin: 0,
                fontSize: "13px",
                color: theme.colors.textPrimary,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                background: m.role === "user" ? "transparent" : theme.colors.bg,
                padding: m.role === "user" ? "0" : "12px 14px",
                borderRadius: m.role === "user" ? "0" : theme.radius.sm,
                border: m.role === "user" ? "none" : `1px solid ${theme.colors.border}`,
              }}
            >
              {m.text}
            </p>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontFamily: theme.font.mono, fontSize: "10px", color: theme.colors.green, letterSpacing: "0.06em" }}>
              {agent.toUpperCase()} AGENT
            </span>
            <span style={{ color: theme.colors.textMuted, fontSize: "13px" }}>thinking…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        style={{
          padding: "14px 20px",
          borderTop: `1px solid ${theme.colors.border}`,
          display: "flex",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask the ${agent} agent…`}
          disabled={loading}
          style={{
            flex: 1,
            padding: "8px 12px",
            background: theme.colors.bg,
            border: `1px solid ${theme.colors.border}`,
            borderRadius: theme.radius.sm,
            color: theme.colors.textPrimary,
            fontFamily: theme.font.mono,
            fontSize: "12px",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            padding: "8px 14px",
            background: theme.colors.green,
            border: "none",
            borderRadius: theme.radius.sm,
            color: "#000",
            fontFamily: theme.font.mono,
            fontWeight: 600,
            fontSize: "12px",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          →
        </button>
      </form>
    </div>
  );
}
