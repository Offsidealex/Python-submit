import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '*.spec.mjs',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'tests/rapport-navigateur', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8765',
    browserName: 'chromium',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'python3 -m http.server 8765 --bind 127.0.0.1',
    url: 'http://127.0.0.1:8765/eleve.html',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
