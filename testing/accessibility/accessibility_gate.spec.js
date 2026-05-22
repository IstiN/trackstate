const { test, expect } = require('@playwright/test');
const {
  collectAccessibilityViolations,
  enableFlutterSemantics,
  formatFlutterSemanticsEvidence,
  formatViolations,
} = require('./accessibility_gate');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/TrackState\.AI/);
  await page.waitForLoadState('networkidle');

  const semanticsEvidence = await enableFlutterSemantics(page);
  console.log(formatFlutterSemanticsEvidence(semanticsEvidence));

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
