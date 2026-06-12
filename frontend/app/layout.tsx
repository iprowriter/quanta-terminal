import type { Metadata } from "next";
import { AuthProvider } from "@/hooks/useAuth";
import Header from "@/components/ui/Header";
import { theme } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Quanta Terminal",
  description: "AI-powered investment research for emerging compute stocks",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
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
          <Header />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
