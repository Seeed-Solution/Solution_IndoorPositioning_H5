import { defineConfig, devices } from '@playwright/test';

/**
 * /map 改造的三视口截图与横向溢出断言。
 *
 * 前置：后端 `uv run python -m server.main`（:8022）与 `npm run dev`（:5173）
 * 都已在跑；这里不代管进程，避免 CI 与本地各起一份。
 */
export default defineConfig({
  testDir: './tests-e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173',
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'desktop-1280',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'tablet-1024',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1024, height: 600 } },
    },
    {
      name: 'mobile-390',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 390, height: 844 },
        isMobile: false,
        hasTouch: true,
      },
    },
  ],
});
