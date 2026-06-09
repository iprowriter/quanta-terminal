"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { theme } from "@/lib/theme";

interface Props {
  onClose: () => void;
}

export default function LoginModal({ onClose }: Props) {
  const { signIn } = useAuth();
  const [email,   setEmail]   = useState("");
  const [status,  setStatus]  = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [errMsg,  setErrMsg]  = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus("sending");
    const { error } = await signIn(email.trim());
    if (error) {
      setErrMsg(error);
      setStatus("error");
    } else {
      setStatus("sent");
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: theme.colors.overlay,
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 200,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: theme.colors.bgPanel,
          border: `1px solid ${theme.colors.borderBright}`,
          borderRadius: theme.radius.lg,
          padding: "40px 36px",
          width: "100%",
          maxWidth: "400px",
          boxShadow: theme.shadow.card,
        }}
      >
        {status === "sent" ? (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "32px", marginBottom: "16px" }}>📬</div>
            <p style={{ color: theme.colors.green, fontFamily: theme.font.mono, fontSize: "14px", marginBottom: "8px" }}>
              MAGIC LINK SENT
            </p>
            <p style={{ color: theme.colors.textSecondary, fontSize: "13px", lineHeight: 1.6 }}>
              Check your inbox for <strong style={{ color: theme.colors.textPrimary }}>{email}</strong>.
              Click the link to sign in.
            </p>
            <button
              onClick={onClose}
              style={{
                marginTop: "24px",
                padding: "8px 24px",
                background: "transparent",
                border: `1px solid ${theme.colors.border}`,
                borderRadius: theme.radius.sm,
                color: theme.colors.textSecondary,
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <h2
              style={{
                margin: "0 0 8px",
                fontFamily: theme.font.mono,
                fontSize: "16px",
                color: theme.colors.green,
                letterSpacing: "0.06em",
              }}
            >
              SIGN IN
            </h2>
            <p style={{ margin: "0 0 28px", color: theme.colors.textSecondary, fontSize: "13px" }}>
              Enter your email — we&apos;ll send a magic link. No password needed.
            </p>

            <form onSubmit={handleSubmit}>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  background: theme.colors.bg,
                  border: `1px solid ${theme.colors.border}`,
                  borderRadius: theme.radius.sm,
                  color: theme.colors.textPrimary,
                  fontFamily: theme.font.mono,
                  fontSize: "13px",
                  outline: "none",
                  boxSizing: "border-box",
                  marginBottom: "16px",
                }}
              />

              {status === "error" && (
                <p style={{ color: theme.colors.red, fontSize: "12px", marginBottom: "12px" }}>
                  {errMsg}
                </p>
              )}

              <button
                type="submit"
                disabled={status === "sending"}
                style={{
                  width: "100%",
                  padding: "11px",
                  background: theme.colors.green,
                  border: "none",
                  borderRadius: theme.radius.sm,
                  color: "#000",
                  fontFamily: theme.font.mono,
                  fontWeight: 600,
                  fontSize: "13px",
                  letterSpacing: "0.06em",
                  cursor: status === "sending" ? "not-allowed" : "pointer",
                  opacity: status === "sending" ? 0.7 : 1,
                }}
              >
                {status === "sending" ? "SENDING…" : "SEND MAGIC LINK →"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
