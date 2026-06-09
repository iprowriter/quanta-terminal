import type { Metadata } from "next";
import { AuthProvider } from "@/hooks/useAuth";
import { theme } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Quanta Terminal",
  description: "AI-powered investment research for emerging compute stocks",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        style={{
          margin: 0,
          padding: 0,
          background: theme.colors.bg,
          color: theme.colors.textPrimary,
          fontFamily: theme.font.sans,
          minHeight: "100vh",
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <AuthProvider>
          {/* Top nav bar */}
          <header
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 32px",
              height: "56px",
              borderBottom: `1px solid ${theme.colors.border}`,
              background: theme.colors.bgPanel,
              position: "sticky",
              top: 0,
              zIndex: 100,
            }}
          >
            <span
              style={{
                fontFamily: theme.font.mono,
                fontSize: "16px",
                fontWeight: 600,
                color: theme.colors.green,
                letterSpacing: "0.08em",
              }}
            >
              ⚡ QUANTA TERMINAL
            </span>
            <span
              style={{
                fontFamily: theme.font.mono,
                fontSize: "11px",
                color: theme.colors.textMuted,
                letterSpacing: "0.1em",
              }}
            >
              AI RESEARCH v0.1
            </span>
          </header>

          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
