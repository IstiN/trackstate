const { test, expect } = require('@playwright/test');
const {
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');
const {
  installTs953NetworkTimeoutSimulation,
} = require('./ts953_network_timeout_simulation');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await installTs953NetworkTimeoutSimulation(page);
  await captureFlutterStartupDiagnostics(page, {
    log: (entry) => console.log(entry),
  });
  await expect(page).toHaveTitle(/TrackState\.AI/);

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
