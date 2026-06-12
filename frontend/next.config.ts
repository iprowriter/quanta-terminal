import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [];
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  disableLogger: true,
  hideSourceMaps: true,
  widenClientFileUpload: true,
});
