const { test, expect } = require('@playwright/test');
const {
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');
const {
  holdTs962CancellationWindow,
} = require('./ts962_accessibility_cancellation_delay');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await captureFlutterStartupDiagnostics(page, {
    log: (entry) => console.log(entry),
  });
  await expect(page).toHaveTitle(/TrackState\.AI/);

  await holdTs962CancellationWindow();
  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
