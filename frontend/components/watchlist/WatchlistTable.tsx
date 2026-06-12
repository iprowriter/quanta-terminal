"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchStocks, type StockQuote } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import LoginModal from "@/components/auth/LoginModal";
import { WatchlistSkeleton } from "@/components/ui/Skeleton";
import { theme } from "@/lib/theme";

function fmt(n: number | null, decimals = 2, prefix = ""): string {
  if (n === null || n === undefined) return "—";
  return `${prefix}${n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function fmtMarketCap(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function fmtVolume(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toString();
}

export default function WatchlistTable() {
  const [stocks,     setStocks]     = useState<StockQuote[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [showLogin,  setShowLogin]  = useState(false);
  const [pendingTicker, setPendingTicker] = useState<string | null>(null);

  const { user } = useAuth();
  const router   = useRouter();

  const load = useCallback(async () => {
    try {
      const data = await fetchStocks();
      setStocks(data);
      setLastUpdate(new Date());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, [load]);

  // After login, resume pending navigation
  useEffect(() => {
    if (user && pendingTicker) {
      router.push(`/memo/${pendingTicker}`);
      setPendingTicker(null);
    }
  }, [user, pendingTicker, router]);

  function handleGenerate(ticker: string) {
    if (!user) {
      setPendingTicker(ticker);
      setShowLogin(true);
    } else {
      router.push(`/memo/${ticker}`);
    }
  }

  return (
    <>
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}


      <div
        style={{
          maxWidth: "1200px",
          margin: "32px auto",
          padding: "0 16px",
        }}
      >
        {/* Page header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: "20px",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <div>
            <h1
              style={{
                margin: 0,
                fontFamily: theme.font.mono,
                fontSize: "clamp(16px, 3vw, 20px)",
                fontWeight: 600,
                color: theme.colors.textPrimary,
                letterSpacing: "0.04em",
              }}
            >
              WATCHLIST
            </h1>
            <p style={{ margin: "4px 0 0", color: theme.colors.textSecondary, fontSize: "12px" }}>
              Emerging compute intelligence — quantum + AI chips
            </p>
          </div>

          {lastUpdate && (
            <span style={{ fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted }}>
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Table — scrollable on mobile */}
        {loading ? (
          <WatchlistSkeleton />
        ) : (
          <div style={{ overflowX: "auto", borderRadius: "8px" }}>
            <table
              style={{
                width: "100%",
                minWidth: "700px",
                borderCollapse: "collapse",
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "8px",
                overflow: "hidden",
                boxShadow: theme.shadow.card,
              }}
            >
              <thead>
                <tr>
                  {[
                    ["TICKER",     "left"],
                    ["COMPANY",    "left"],
                    ["PRICE",      "right"],
                    ["CHANGE",     "right"],
                    ["MARKET CAP", "right"],
                    ["VOLUME",     "right"],
                    ["ACTION",     "right"],
                  ].map(([label, align]) => (
                    <th
                      key={label}
                      style={{
                        padding: "10px 16px",
                        textAlign: align as "left" | "right",
                        fontFamily: theme.font.mono,
                        fontSize: "11px",
                        color: theme.colors.textMuted,
                        letterSpacing: "0.1em",
                        fontWeight: 500,
                        borderBottom: `1px solid ${theme.colors.borderBright}`,
                        background: theme.colors.bgPanel,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stocks.map((s) => {
                  const pos = s.change_pct !== null && s.change_pct > 0;
                  const neg = s.change_pct !== null && s.change_pct < 0;

                  const cell = (align: "left" | "right" = "right"): React.CSSProperties => ({
                    padding: "13px 16px",
                    textAlign: align,
                    fontFamily: theme.font.mono,
                    fontSize: "13px",
                    borderBottom: `1px solid ${theme.colors.border}`,
                    whiteSpace: "nowrap",
                  });

                  return (
                    <tr
                      key={s.ticker}
                      style={{ background: theme.colors.bgPanel, transition: "background 0.1s" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = theme.colors.bgHover)}
                      onMouseLeave={(e) => (e.currentTarget.style.background = theme.colors.bgPanel)}
                    >
                      <td style={{ ...cell("left"), color: theme.colors.cyan, fontWeight: 600 }}>
                        {s.ticker}
                      </td>
                      <td style={{ ...cell("left"), color: theme.colors.textSecondary, fontFamily: theme.font.sans, fontSize: "13px" }}>
                        {s.name}
                      </td>
                      <td style={{ ...cell(), color: theme.colors.textPrimary }}>
                        {fmt(s.price, 2, "$")}
                      </td>
                      <td style={{ ...cell(), color: pos ? theme.colors.green : neg ? theme.colors.red : theme.colors.textMuted, fontWeight: 500 }}>
                        {s.change_pct === null ? "—" : `${pos ? "+" : ""}${fmt(s.change_pct)}%`}
                      </td>
                      <td style={{ ...cell(), color: theme.colors.textSecondary }}>
                        {fmtMarketCap(s.market_cap)}
                      </td>
                      <td style={{ ...cell(), color: theme.colors.textSecondary }}>
                        {fmtVolume(s.volume)}
                      </td>
                      <td style={cell()}>
                        <button
                          onClick={() => handleGenerate(s.ticker)}
                          style={{
                            padding: "5px 12px",
                            background: "transparent",
                            border: `1px solid ${theme.colors.green}`,
                            borderRadius: theme.radius.sm,
                            color: theme.colors.green,
                            fontFamily: theme.font.mono,
                            fontSize: "11px",
                            cursor: "pointer",
                            letterSpacing: "0.06em",
                            whiteSpace: "nowrap",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,255,136,0.1)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                        >
                          MEMO →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
