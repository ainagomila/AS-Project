import { defineConfig, devices } from '@playwright/test'
import { FRONTEND_BASE_URL } from './src/test/e2e/support/env'

const shouldStartDevServer = !process.env.E2E_BASE_URL

const DEV_SERVER_URL = 'https://127.0.0.1:4173'
const DEFAULT_CI_WORKERS = 4

// Keep worker logic centralized so both local and CI runs stay configurable.
const resolveWorkers = () => {
  if (process.env.PLAYWRIGHT_WORKERS) {
    const parsed = Number(process.env.PLAYWRIGHT_WORKERS)
    if (!Number.isNaN(parsed) && parsed > 0) {
      return parsed
    }
  }

  return process.env.CI ? DEFAULT_CI_WORKERS : undefined
}

export default defineConfig({
  testDir: './src/test/e2e',
  timeout: 90_000,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: resolveWorkers(),
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: FRONTEND_BASE_URL,
    ignoreHTTPSErrors: true,
    // Bounded steps: a stuck click or page load fails on that step, not as a bare test timeout.
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 720 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: shouldStartDevServer
    ? {
      command: 'node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4173',
      url: DEV_SERVER_URL,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    }
    : undefined,
})
