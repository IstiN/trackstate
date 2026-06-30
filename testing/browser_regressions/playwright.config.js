const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  timeout: 120000,
  expect: {
    timeout: 15000,
  },
  use: {
    baseURL: 'http://127.0.0.1:4173',
    browserName: 'chromium',
    headless: true,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npx http-server ../../build/web -p 4173 -c-1',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 120000,
  },
});
