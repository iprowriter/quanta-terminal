/**
 * Design tokens — dark terminal aesthetic.
 * Import and use in inline styles throughout the app.
 */

export const theme = {
  colors: {
    bg:           "#0a0a0f",   // near-black page background
    bgPanel:      "#0f0f1a",   // slightly lighter panels / cards
    bgHover:      "#141428",   // row hover state
    border:       "#1e1e3a",   // subtle borders
    borderBright: "#2a2a50",   // focused / active borders

    green:        "#00ff88",   // primary accent — prices, success, CTA
    greenDim:     "#00cc6a",   // hover state for green elements
    cyan:         "#00d4ff",   // secondary accent — links, labels
    red:          "#ff4466",   // negative change, errors
    yellow:       "#ffd600",   // warnings, neutral signals

    textPrimary:  "#e8e8f0",   // headings, important values
    textSecondary:"#8888aa",   // labels, secondary info
    textMuted:    "#6b6b8a",   // placeholder, disabled

    overlay:      "rgba(0,0,0,0.7)",
  },

  font: {
    mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },

  radius: {
    sm: "4px",
    md: "8px",
    lg: "12px",
  },

  shadow: {
    card: "0 4px 24px rgba(0,0,0,0.6)",
    glow: "0 0 20px rgba(0,255,136,0.15)",
  },
} as const;
