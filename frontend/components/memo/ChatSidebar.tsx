"use client";

import { useState, useRef, useEffect } from "react";
import { sendChat, type AgentName } from "@/lib/api";
import { useTypewriter } from "@/hooks/useTypewriter";
import { theme } from "@/lib/theme";

const AGENTS: { value: AgentName; label: string }[] = [
  { value: "analyst",  label: "Analyst" },
  { value: "earnings", label: "Earnings" },
  { value: "sec",      label: "SEC" },
  { value: "news",     label: "News" },
  { value: "tech",     label: "Tech" },
];

interface Message {
  id:    number;
  role:  "user" | "assistant";
  text:  string;
  agent: AgentName;
}

interface Props {
  ticker:      string;
  accessToken: string;
}

// Renders a single assistant message with optional typewriter animation
function AssistantMessage({
  message,
  animate,
}: {
  message: Message;
  animate: boolean;
}) {
  const displayed = useTypewriter(animate ? message.text : "", { speed: 8, delay: 16 });
  const text      = animate ? displayed : message.text;
  const showCursor = animate && displayed.length < message.text.length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <span
        style={{
          fontFamily: theme.font.mono,
          fontSize: "10px",
          color: theme.colors.green,
          letterSpacing: "0.06em",
        }}
      >
        {message.agent.toUpperCase()} AGENT
      </span>
      <p
        style={{
          margin: 0,
          fontSize: "13px",
          color: theme.colors.textPrimary,
          lineHeight: 1.7,
          whiteSpace: "pre-wrap",
          background: theme.colors.bg,
          padding: "12px 14px",
          borderRadius: theme.radius.sm,
          border: `1px solid ${theme.colors.border}`,
          wordBreak: "break-word",
        }}
      >
        {text}
        {showCursor && (
          <span
            style={{
              display: "inline-block",
              width: "2px",
              height: "14px",
              background: theme.colors.green,
              marginLeft: "2px",
              verticalAlign: "middle",
              animation: "blink 0.7s step-end infinite",
            }}
          />
        )}
        <style>{`
          @keyframes blink {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0; }
          }
        `}</style>
      </p>
    </div>
  );
}

export default function ChatSidebar({ ticker, accessToken }: Props) {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [agent,     setAgent]     = useState<AgentName>("analyst");
  const [threadId,  setThreadId]  = useState<string | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [latestId,  setLatestId]  = useState<number | null>(null);
  const idRef     = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userId = ++idRef.current;
    setMessages((m) => [...m, { id: userId, role: "user", text, agent }]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(ticker, text, agent, threadId, accessToken);
      setThreadId(res.thread_id);

      const assistantId = ++idRef.current;
      setLatestId(assistantId);
      setMessages((m) => [
        ...m,
        { id: assistantId, role: "assistant", text: res.text, agent: res.agent },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Request failed";
      const errId = ++idRef.current;
      setLatestId(errId);
      setMessages((m) => [
        ...m,
        { id: errId, role: "assistant", text: `Error: ${msg}`, agent },
      ]);
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
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: `1px solid ${theme.colors.border}`,
          flexShrink: 0,
        }}
      >
        <p style={{ margin: "0 0 10px", fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted, letterSpacing: "0.1em" }}>
          CHAT WITH SPECIALIST
        </p>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
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

      {/* Messages */}
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

        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <span style={{ fontFamily: theme.font.mono, fontSize: "10px", color: theme.colors.cyan, letterSpacing: "0.06em" }}>
                YOU
              </span>
              <p style={{ margin: 0, fontSize: "13px", color: theme.colors.textSecondary, lineHeight: 1.6 }}>
                {m.text}
              </p>
            </div>
          ) : (
            <AssistantMessage
              key={m.id}
              message={m}
              animate={m.id === latestId}
            />
          )
        )}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontFamily: theme.font.mono, fontSize: "10px", color: theme.colors.green, letterSpacing: "0.06em" }}>
              {agent.toUpperCase()} AGENT
            </span>
            <span style={{ color: theme.colors.textMuted, fontSize: "13px", fontFamily: theme.font.mono }}>
              thinking
              <span style={{ animation: "dots 1.2s steps(3,end) infinite" }}>...</span>
            </span>
            <style>{`
              @keyframes dots {
                0%  { clip-path: inset(0 66% 0 0); }
                33% { clip-path: inset(0 33% 0 0); }
                66% { clip-path: inset(0 0 0 0); }
              }
            `}</style>
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
