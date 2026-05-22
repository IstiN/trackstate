const { test, expect } = require('@playwright/test');
const {
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');
const {
  createTs943SilentEngineLogger,
} = require('./ts943_silent_engine_logger');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  const silentEngineLogger = createTs943SilentEngineLogger();
  await captureFlutterStartupDiagnostics(page, {
    log: silentEngineLogger,
  });
  await expect(page).toHaveTitle(/TrackState\.AI/);

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
