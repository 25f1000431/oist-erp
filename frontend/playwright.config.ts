import { defineConfig } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { tmpdir } from "node:os";

const frontendDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(frontendDir, "..");
const envPath = resolve(repoRoot, ".env");
const databaseFile = resolve(tmpdir(), `oist-erp-playwright-${process.pid}.sqlite`);
const resultsDir = resolve(tmpdir(), `oist-erp-playwright-results-${process.pid}`);

if (!process.env.SEED_DEFAULT_PASSWORD) {
  try {
    const envText = readFileSync(envPath, "utf8");
    const match = envText.match(/^\s*SEED_DEFAULT_PASSWORD\s*=\s*(.*?)\s*$/m);
    const value = match?.[1]?.replace(/^(["'])(.*)\1$/, "$2");
    if (value) process.env.SEED_DEFAULT_PASSWORD = value;
  } catch {
    // The message below gives the required local setup without exposing a secret.
  }
}

if (!process.env.SEED_DEFAULT_PASSWORD) {
  throw new Error("Set SEED_DEFAULT_PASSWORD in the project .env before running Playwright.");
}

const env = {
  ...process.env,
  DATABASE_URL: `sqlite:///${databaseFile}`,
  E2E_SQLITE_FILE: databaseFile,
  E2E_RESULTS_DIR: resultsDir,
  E2E_API_PORT: "18000",
  FRONTEND_ORIGINS: "http://127.0.0.1:15173",
  VITE_API_BASE_URL: "http://127.0.0.1:18000/api/v1",
  PYTHONPATH: "backend",
  UV_CACHE_DIR: resolve(tmpdir(), "oist-uv-cache"),
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  outputDir: resultsDir,
  globalTeardown: "./e2e/cleanup.ts",
  use: {
    baseURL: "http://127.0.0.1:15173",
    headless: true,
    trace: "off",
  },
  webServer: [
    {
      command: "uv run python scripts/e2e_api_server.py",
      cwd: repoRoot,
      url: "http://127.0.0.1:18000/health",
      env,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 15173 --strictPort",
      cwd: frontendDir,
      url: "http://127.0.0.1:15173/login",
      env,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
