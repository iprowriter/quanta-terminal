import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Capture 100% of traces in dev, 10% in production
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Only enable in production — avoids noise during dev
  enabled: true,
  //enabled: process.env.NODE_ENV === "production",

  integrations: [
    Sentry.replayIntegration({
      // Mask all text and block all images to protect user privacy
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // Capture 10% of sessions for session replay
  replaysSessionSampleRate: 0.1,
  // Capture 100% of sessions with errors
  replaysOnErrorSampleRate: 1.0,
});
