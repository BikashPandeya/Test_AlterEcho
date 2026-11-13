import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  reporter: [["line"]],
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 }, acceptDownloads: true } }],
  webServer: [
    { command: ".venv-geo\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000", cwd: "../backend", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: true, timeout: 30_000 },
    { command: "npm.cmd run dev", cwd: ".", url: "http://localhost:3000", reuseExistingServer: true, timeout: 60_000 },
  ],
});

