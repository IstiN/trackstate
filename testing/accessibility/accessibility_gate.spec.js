const { test, expect } = require('@playwright/test');
const { AxeBuilder } = require('@axe-core/playwright');

const accessibilityGateRules = [
  'aria-command-name',
  'aria-input-field-name',
  'button-name',
  'color-contrast',
  'input-button-name',
  'link-name',
];

function formatViolations(violations) {
  if (violations.length === 0) {
    return 'Expected no accessibility violations.';
  }

  return violations
      .map((violation) => {
        const nodes = violation.nodes
            .map((node) => {
              const target = node.target.join(' -> ');
              const summary =
                  node.failureSummary?.replace(/\s+/g, ' ').trim() ?? 'No summary';
              return `      - ${target}: ${summary}`;
            })
            .join('\n');
        return `${violation.id}: ${violation.help}\n${nodes}`;
      })
      .join('\n');
}

async function enableFlutterSemantics(page) {
  const placeholder = page.locator('flt-semantics-placeholder');
  await expect(placeholder).toHaveCount(1);
  await placeholder.evaluate((element) => {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await expect(page.locator('flt-semantics-host')).toHaveCount(1, {
    timeout: 15000,
  });
  await expect
      .poll(async () => await page.locator('flt-semantics').count())
      .toBeGreaterThan(0);
}

test('TrackState web app has no axe-core accessibility violations', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/TrackState\.AI/);
  await page.waitForLoadState('networkidle');

  await enableFlutterSemantics(page);

  const results = await new AxeBuilder({ page })
      // Flutter web adds engine-owned DOM such as viewport/meta, hidden text
      // inputs, and tabindex bridges that produce unrelated noise in axe.
      // The gate stays focused on the ticket's required contributor-authored
      // failures: contrast defects and missing accessible names.
      .withRules(accessibilityGateRules)
      .analyze();

  expect(results.violations, formatViolations(results.violations)).toEqual([]);
});
