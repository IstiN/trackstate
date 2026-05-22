const { test, expect } = require('@playwright/test');
const {
  collectAccessibilityViolations,
  enableFlutterSemantics,
  formatFlutterSemanticsEvidence,
  formatViolations,
} = require('./accessibility_gate');
const {
  installTs933SemanticsFailureSimulation,
} = require('./ts933_semantics_failure_simulation');

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await installTs933SemanticsFailureSimulation(page);
  await page.goto('/');
  await expect(page).toHaveTitle(/TrackState\.AI/);
  await page.waitForLoadState('networkidle');

  const semanticsEvidence = await enableFlutterSemantics(page);
  console.log(formatFlutterSemanticsEvidence(semanticsEvidence));

  const results = await collectAccessibilityViolations(page);

  expect(results, formatViolations(results)).toEqual([]);
});
