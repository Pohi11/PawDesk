import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a self-contained server (.next/standalone) for a small Docker image.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  // The Try page moved to the home page (spec: run-dashboard). Temporary, so browsers don't
  // cache it if /demo is reused later.
  async redirects() {
    return [{ source: "/demo", destination: "/", permanent: false }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
