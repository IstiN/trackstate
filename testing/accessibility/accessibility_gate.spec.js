const { test, expect } = require('@playwright/test');
const {
  collectAccessibilityViolations,
  enableFlutterSemantics,
  formatViolations,
} = require('./accessibility_gate');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/TrackState\.AI/);
  await page.waitForLoadState('networkidle');

  await enableFlutterSemantics(page);

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
