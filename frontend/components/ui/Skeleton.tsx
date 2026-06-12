"use client";

import { theme } from "@/lib/theme";

interface Props {
  width?:  string | number;
  height?: string | number;
  style?:  React.CSSProperties;
}

/**
 * Animated shimmer skeleton block for loading states.
 */
export default function Skeleton({ width = "100%", height = "16px", style }: Props) {
  return (
    <span
      style={{
        display: "inline-block",
        width,
        height,
        borderRadius: "4px",
        background: `linear-gradient(90deg, ${theme.colors.bgPanel} 25%, ${theme.colors.bgHover} 50%, ${theme.colors.bgPanel} 75%)`,
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite",
        ...style,
      }}
    >
      <style>{`
        @keyframes shimmer {
          0%   { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </span>
  );
}

/** A full watchlist table skeleton — 8 placeholder rows. */
export function WatchlistSkeleton() {
  return (
    <div
      style={{
        borderRadius: "8px",
        border: `1px solid ${theme.colors.border}`,
        overflow: "hidden",
        boxShadow: "0 4px 24px rgba(0,0,0,0.6)",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "80px 1fr 100px 100px 130px 100px 140px",
          padding: "10px 20px",
          borderBottom: `1px solid ${theme.colors.borderBright}`,
          background: theme.colors.bgPanel,
          gap: "16px",
        }}
      >
        {["TICKER","COMPANY","PRICE","CHANGE","MARKET CAP","VOLUME","ACTION"].map((h) => (
          <span key={h} style={{ fontFamily: "monospace", fontSize: "11px", color: theme.colors.textMuted, letterSpacing: "0.1em" }}>
            {h}
          </span>
        ))}
      </div>

      {/* Skeleton rows */}
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          style={{
            display: "grid",
            gridTemplateColumns: "80px 1fr 100px 100px 130px 100px 140px",
            padding: "14px 20px",
            borderBottom: `1px solid ${theme.colors.border}`,
            background: theme.colors.bgPanel,
            gap: "16px",
            alignItems: "center",
          }}
        >
          <Skeleton width="48px" height="14px" />
          <Skeleton width="60%" height="14px" />
          <Skeleton width="70px" height="14px" style={{ marginLeft: "auto" }} />
          <Skeleton width="60px" height="14px" style={{ marginLeft: "auto" }} />
          <Skeleton width="80px" height="14px" style={{ marginLeft: "auto" }} />
          <Skeleton width="60px" height="14px" style={{ marginLeft: "auto" }} />
          <Skeleton width="110px" height="26px" style={{ borderRadius: "4px", marginLeft: "auto" }} />
        </div>
      ))}
    </div>
  );
}
