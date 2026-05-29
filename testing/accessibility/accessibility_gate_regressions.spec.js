const assert = require('node:assert/strict');
const { test, expect } = require('@playwright/test');
const {
  collectAccessibilityViolations,
  enableFlutterSemantics,
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

  test('surfaces a descriptive semantics initialization error on timeout', async () => {
    const fakePage = {
      async waitForSelector() {},
      locator() {
        return {
          async evaluate() {},
        };
      },
      async waitForFunction() {
        const error = new Error(
            'page.waitForFunction: Test timeout of 120000ms exceeded',
        );
        error.name = 'TimeoutError';
        throw error;
      },
      async evaluate() {
        return {
          placeholderCount: 1,
          hostCount: 1,
          nodeCount: 0,
          sampleLabels: [],
        };
      },
    };

    await assert.rejects(
        () => enableFlutterSemantics(fakePage),
        (error) => {
          assert.match(
              error.message,
              /Flutter engine failed to render semantics nodes during initialization/,
          );
          assert.match(error.message, /placeholder-count=1/);
          assert.match(error.message, /host-count=1/);
          assert.match(error.message, /node-count=0/);
          assert.doesNotMatch(error.message, /page\.waitForFunction/);
          return true;
        },
    );
  });

  test('rethrows non-timeout waitForFunction failures unchanged', async () => {
    const pageClosedError = new Error(
        'page.waitForFunction: Target page, context or browser has been closed',
    );
    const fakePage = {
      async waitForSelector() {},
      locator() {
        return {
          async evaluate() {},
        };
      },
      async waitForFunction() {
        throw pageClosedError;
      },
    };

    await assert.rejects(
        () => enableFlutterSemantics(fakePage),
        (error) => {
          assert.strictEqual(error, pageClosedError);
          return true;
        },
    );
  });
});
