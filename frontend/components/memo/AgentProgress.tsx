"use client";

import { theme } from "@/lib/theme";

const AGENTS = [
  { key: "sec",         label: "SEC Filings" },
  { key: "earnings",    label: "Earnings" },
  { key: "analyst",     label: "Analyst & Valuation" },
  { key: "news",        label: "News & Sentiment" },
  { key: "research",    label: "Research & Technology" },
  { key: "memo_writer", label: "Writing Memo" },
];

interface Props {
  completed: Set<string>;
  active:    boolean;   // pipeline still running
}

export default function AgentProgress({ completed, active }: Props) {
  return (
    <div
      style={{
        background: theme.colors.bgPanel,
        border: `1px solid ${theme.colors.border}`,
        borderRadius: theme.radius.md,
        padding: "24px",
        marginBottom: "28px",
      }}
    >
      <p
        style={{
          margin: "0 0 16px",
          fontFamily: theme.font.mono,
          fontSize: "11px",
          color: theme.colors.textMuted,
          letterSpacing: "0.1em",
        }}
      >
        {active ? "RUNNING PIPELINE…" : "PIPELINE COMPLETE"}
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {AGENTS.map(({ key, label }, i) => {
          const done    = completed.has(key);
          const running = active && !done && i === completed.size; // next in line
          return (
            <div
              key={key}
              style={{ display: "flex", alignItems: "center", gap: "12px" }}
            >
              {/* Status dot */}
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: done
                    ? theme.colors.green
                    : running
                    ? theme.colors.yellow
                    : theme.colors.textMuted,
                  flexShrink: 0,
                  boxShadow: done
                    ? `0 0 6px ${theme.colors.green}`
                    : running
                    ? `0 0 6px ${theme.colors.yellow}`
                    : "none",
                  transition: "background 0.3s",
                }}
              />

              <span
                style={{
                  fontFamily: theme.font.mono,
                  fontSize: "12px",
                  color: done
                    ? theme.colors.textPrimary
                    : running
                    ? theme.colors.yellow
                    : theme.colors.textMuted,
                  transition: "color 0.3s",
                }}
              >
                {label}
              </span>

              {done && (
                <span
                  style={{
                    fontFamily: theme.font.mono,
                    fontSize: "10px",
                    color: theme.colors.green,
                  }}
                >
                  ✓
                </span>
              )}

              {running && (
                <span
                  style={{
                    fontFamily: theme.font.mono,
                    fontSize: "10px",
                    color: theme.colors.yellow,
                  }}
                >
                  …
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
