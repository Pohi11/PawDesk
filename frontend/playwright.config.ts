import { defineConfig, devices } from "@playwright/test";

// End-to-end tests (spec: delivery-pipeline): the real API on a fresh seeded database with
// recorded model responses (scripts/e2e_server.py), and the dashboard in front of it.
// Record new responses with PAWDESK_E2E_RECORD=1 (real model calls); CI always replays.
const API_PORT = 8011;
const WEB_PORT = 3011;

export default defineConfig({
  testDir: "./e2e",
  // Its own folder: Playwright empties outputDir on every run, and test-results/ also holds
  // the unit tests' report.
  outputDir: "test-results/e2e",
  timeout: 120_000,
  expect: { timeout: 60_000 },
  fullyParallel: false,
  workers: 1, // the tests share one database and run in order
  reporter: [["list"], ["junit", { outputFile: "test-results/e2e-junit.xml" }]],
  use: { baseURL: `http://localhost:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } }],
  webServer: [
    {
      command: "uv --directory ../backend run python -m scripts.e2e_server",
      url: `http://127.0.0.1:${API_PORT}/health`,
      timeout: 180_000,
      reuseExistingServer: false,
    },
    {
      command: `pnpm exec next dev --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      env: { BACKEND_URL: `http://127.0.0.1:${API_PORT}` },
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
