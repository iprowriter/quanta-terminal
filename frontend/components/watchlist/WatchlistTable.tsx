"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchStocks, type StockQuote } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import LoginModal from "@/components/auth/LoginModal";
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

  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

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

  // Initial load + 60s refresh
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

  const colStyle = (align: "left" | "right" = "right"): React.CSSProperties => ({
    padding: "14px 20px",
    textAlign: align,
    fontFamily: theme.font.mono,
    fontSize: "13px",
    borderBottom: `1px solid ${theme.colors.border}`,
    whiteSpace: "nowrap",
  });

  const headStyle = (align: "left" | "right" = "right"): React.CSSProperties => ({
    ...colStyle(align),
    color: theme.colors.textMuted,
    fontSize: "11px",
    letterSpacing: "0.1em",
    fontWeight: 500,
    padding: "10px 20px",
    borderBottom: `1px solid ${theme.colors.borderBright}`,
    background: theme.colors.bgPanel,
  });

  return (
    <>
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}

      <div
        style={{
          maxWidth: "1200px",
          margin: "40px auto",
          padding: "0 24px",
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: "20px",
          }}
        >
          <div>
            <h1
              style={{
                margin: 0,
                fontFamily: theme.font.mono,
                fontSize: "20px",
                fontWeight: 600,
                color: theme.colors.textPrimary,
                letterSpacing: "0.04em",
              }}
            >
              WATCHLIST
            </h1>
            <p style={{ margin: "4px 0 0", color: theme.colors.textSecondary, fontSize: "12px" }}>
              Emerging compute intelligence — quantum + AI
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {lastUpdate && (
              <span style={{ fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.textMuted }}>
                Updated {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            {!authLoading && (
              user ? (
                <span style={{ fontFamily: theme.font.mono, fontSize: "11px", color: theme.colors.green }}>
                  ● {user.email}
                </span>
              ) : (
                <button
                  onClick={() => setShowLogin(true)}
                  style={{
                    padding: "6px 14px",
                    background: "transparent",
                    border: `1px solid ${theme.colors.green}`,
                    borderRadius: theme.radius.sm,
                    color: theme.colors.green,
                    fontFamily: theme.font.mono,
                    fontSize: "11px",
                    cursor: "pointer",
                    letterSpacing: "0.06em",
                  }}
                >
                  SIGN IN
                </button>
              )
            )}
          </div>
        </div>

        {/* Table */}
        <div
          style={{
            borderRadius: theme.radius.md,
            border: `1px solid ${theme.colors.border}`,
            overflow: "hidden",
            boxShadow: theme.shadow.card,
          }}
        >
          {loading ? (
            <div style={{ padding: "60px", textAlign: "center", color: theme.colors.textMuted, fontFamily: theme.font.mono, fontSize: "13px" }}>
              LOADING MARKET DATA…
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={headStyle("left")}>TICKER</th>
                  <th style={headStyle("left")}>COMPANY</th>
                  <th style={headStyle()}>PRICE</th>
                  <th style={headStyle()}>CHANGE</th>
                  <th style={headStyle()}>MARKET CAP</th>
                  <th style={headStyle()}>VOLUME</th>
                  <th style={headStyle()}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((s) => {
                  const isPositive = s.change_pct !== null && s.change_pct > 0;
                  const isNegative = s.change_pct !== null && s.change_pct < 0;
                  return (
                    <tr
                      key={s.ticker}
                      style={{ background: theme.colors.bgPanel }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background = theme.colors.bgHover)
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = theme.colors.bgPanel)
                      }
                    >
                      <td style={{ ...colStyle("left"), color: theme.colors.cyan, fontWeight: 600 }}>
                        {s.ticker}
                      </td>
                      <td style={{ ...colStyle("left"), color: theme.colors.textSecondary, fontFamily: theme.font.sans }}>
                        {s.name}
                      </td>
                      <td style={{ ...colStyle(), color: theme.colors.textPrimary }}>
                        {fmt(s.price, 2, "$")}
                      </td>
                      <td style={{
                        ...colStyle(),
                        color: isPositive ? theme.colors.green : isNegative ? theme.colors.red : theme.colors.textMuted,
                        fontWeight: 500,
                      }}>
                        {s.change_pct === null ? "—" : `${isPositive ? "+" : ""}${fmt(s.change_pct)}%`}
                      </td>
                      <td style={{ ...colStyle(), color: theme.colors.textSecondary }}>
                        {fmtMarketCap(s.market_cap)}
                      </td>
                      <td style={{ ...colStyle(), color: theme.colors.textSecondary }}>
                        {fmtVolume(s.volume)}
                      </td>
                      <td style={colStyle()}>
                        <button
                          onClick={() => handleGenerate(s.ticker)}
                          style={{
                            padding: "5px 14px",
                            background: "transparent",
                            border: `1px solid ${theme.colors.green}`,
                            borderRadius: theme.radius.sm,
                            color: theme.colors.green,
                            fontFamily: theme.font.mono,
                            fontSize: "11px",
                            cursor: "pointer",
                            letterSpacing: "0.06em",
                            transition: "background 0.15s",
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = "rgba(0,255,136,0.1)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = "transparent";
                          }}
                        >
                          GENERATE MEMO →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
