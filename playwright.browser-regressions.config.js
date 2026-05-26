const { defineConfig } = require('@playwright/test');
const baseConfig = require('./playwright.config');

module.exports = defineConfig({
  ...baseConfig,
  testDir: './testing/browser_regressions',
});
