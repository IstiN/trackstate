const { test, expect } = require('@playwright/test');

const {
  collectAccessibilityViolations,
  formatViolations,
} = require('./accessibility_gate');

test.describe('accessibility gate regressions', () => {
  test('flags Flutter runtime contrast probe markers', async ({ page }) => {
    await page.setContent(`
      <!doctype html>
      <html lang="en">
        <body>
          <div
            id="trackstate-accessibility-probe-color-contrast"
            data-trackstate-accessibility-probe="color-contrast"
            data-trackstate-contrast-ratio="1.00"
            data-trackstate-contrast-threshold="4.5"
            data-trackstate-foreground="#faf8f4"
            data-trackstate-background="#faf8f4"
            data-trackstate-text="Sync issue"
            data-trackstate-semantics-label="button"
            hidden
          ></div>
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
