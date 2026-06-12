"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import LoginModal from "@/components/auth/LoginModal";
import { theme } from "@/lib/theme";

export default function Header() {
  const { user, signOut, loading } = useAuth();
  const [showLogin,   setShowLogin]   = useState(false);
  const [menuOpen,    setMenuOpen]    = useState(false);
  const [signingOut,  setSigningOut]  = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    setMenuOpen(false);
    setSigningOut(false);
  }

  return (
    <>
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}

      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          height: "56px",
          borderBottom: `1px solid ${theme.colors.border}`,
          background: theme.colors.bgPanel,
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        {/* Logo */}
        <a
          href="/"
          style={{
            fontFamily: theme.font.mono,
            fontSize: "15px",
            fontWeight: 600,
            color: theme.colors.green,
            letterSpacing: "0.08em",
            textDecoration: "none",
          }}
        >
          ⚡ <span style={{ display: "none" }}>QUANTA </span>
          <span>QUANTA TERMINAL</span>
        </a>

        {/* Right side */}
        {!loading && (
          <div style={{ position: "relative" }}>
            {user ? (
              <>
                <button
                  onClick={() => setMenuOpen((o) => !o)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "5px 12px",
                    background: menuOpen ? "rgba(0,255,136,0.08)" : "transparent",
                    border: `1px solid ${menuOpen ? theme.colors.green : theme.colors.border}`,
                    borderRadius: theme.radius.sm,
                    color: theme.colors.green,
                    fontFamily: theme.font.mono,
                    fontSize: "11px",
                    cursor: "pointer",
                    letterSpacing: "0.04em",
                  }}
                >
                  <span
                    style={{
                      width: "7px", height: "7px",
                      borderRadius: "50%",
                      background: theme.colors.green,
                      boxShadow: `0 0 6px ${theme.colors.green}`,
                      flexShrink: 0,
                    }}
                  />
                  {/* Hide email on small screens */}
                  <span
                    style={{
                      maxWidth: "180px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {user.email}
                  </span>
                  <span style={{ color: theme.colors.textMuted }}>▾</span>
                </button>

                {menuOpen && (
                  <div
                    style={{
                      position: "absolute",
                      right: 0,
                      top: "calc(100% + 8px)",
                      background: theme.colors.bgPanel,
                      border: `1px solid ${theme.colors.borderBright}`,
                      borderRadius: theme.radius.md,
                      minWidth: "200px",
                      boxShadow: theme.shadow.card,
                      overflow: "hidden",
                      zIndex: 200,
                    }}
                  >
                    {/* User info */}
                    <div
                      style={{
                        padding: "12px 16px",
                        borderBottom: `1px solid ${theme.colors.border}`,
                      }}
                    >
                      <p style={{ margin: 0, fontFamily: theme.font.mono, fontSize: "10px", color: theme.colors.textMuted, letterSpacing: "0.08em" }}>
                        SIGNED IN AS
                      </p>
                      <p style={{ margin: "4px 0 0", fontFamily: theme.font.mono, fontSize: "12px", color: theme.colors.textPrimary, wordBreak: "break-all" }}>
                        {user.email}
                      </p>
                    </div>

                    {/* Sign out */}
                    <button
                      onClick={handleSignOut}
                      disabled={signingOut}
                      style={{
                        width: "100%",
                        padding: "12px 16px",
                        background: "transparent",
                        border: "none",
                        textAlign: "left",
                        color: theme.colors.red,
                        fontFamily: theme.font.mono,
                        fontSize: "12px",
                        cursor: "pointer",
                        letterSpacing: "0.04em",
                        opacity: signingOut ? 0.6 : 1,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,68,102,0.08)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      {signingOut ? "SIGNING OUT…" : "SIGN OUT →"}
                    </button>
                  </div>
                )}

                {/* Click outside to close */}
                {menuOpen && (
                  <div
                    onClick={() => setMenuOpen(false)}
                    style={{ position: "fixed", inset: 0, zIndex: 150 }}
                  />
                )}
              </>
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
            )}
          </div>
        )}
      </header>
    </>
  );
}
