const { test, expect } = require('@playwright/test');

const {
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');

test.describe('accessibility gate regressions', () => {
  test('flags WCAG AA contrast regressions', async ({ page }) => {
    await page.setContent(`
      <!doctype html>
      <html lang="en">
        <body>
          <button style="color: #9c9c9c; background: #ffffff;">Save changes</button>
        </body>
      </html>
    `);

    const violations = await collectAccessibilityViolations(page);

    expect(violations, formatViolations(violations)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ id: 'color-contrast' }),
        ]),
    );
  });

  test('flags non-descriptive interactive labels', async ({ page }) => {
    await page.setContent(`
      <!doctype html>
      <html lang="en">
        <body>
          <button aria-label="button">
            <span aria-hidden="true">+</span>
          </button>
        </body>
      </html>
    `);

    const violations = await collectAccessibilityViolations(page);

    expect(violations, formatViolations(violations)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ id: 'non-descriptive-label' }),
        ]),
    );
  });

  test('allows descriptive interactive labels', async ({ page }) => {
    await page.setContent(`
      <!doctype html>
      <html lang="en">
        <body>
          <button aria-label="Create tracker">
            <span aria-hidden="true">+</span>
          </button>
        </body>
      </html>
    `);

    const violations = await collectAccessibilityViolations(page);

    expect(violations, formatViolations(violations)).toEqual([]);
  });
});
