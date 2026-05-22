const fs = require('fs');
const path = require('path');
const { test, expect } = require('@playwright/test');

const {
  collectAccessibilityViolations,
  formatViolations,
} = require('../../accessibility/accessibility_gate');

const VISIBLE_TEXT = 'Boundary contrast sample';
const BUTTON_LABEL = 'Open tracker settings';
const TEXT_COLOR = 'rgb(50, 50, 50)';
const BACKGROUND_COLOR = 'rgb(153, 153, 153)';

function parseCssColor(value) {
  const match = value.match(/rgba?\(([^)]+)\)/i);
  if (!match) {
    throw new Error(`Unsupported CSS color: ${value}`);
  }

  const channels = match[1].split(',').map((entry) => Number(entry.trim()));
  const [red, green, blue, alpha = 1] = channels;
  return { red, green, blue, alpha };
}

function compositeColor(foreground, background) {
  const alpha = foreground.alpha;
  return {
    red: foreground.red * alpha + background.red * (1 - alpha),
    green: foreground.green * alpha + background.green * (1 - alpha),
    blue: foreground.blue * alpha + background.blue * (1 - alpha),
  };
}

function normalizeSrgb(channel) {
  const normalized = channel / 255;
  return normalized <= 0.04045
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(color) {
  return (
    0.2126 * normalizeSrgb(color.red) +
    0.7152 * normalizeSrgb(color.green) +
    0.0722 * normalizeSrgb(color.blue)
  );
}

function contrastRatio(foreground, background) {
  const lighter = Math.max(
      relativeLuminance(foreground),
      relativeLuminance(background),
  );
  const darker = Math.min(
      relativeLuminance(foreground),
      relativeLuminance(background),
  );
  return (lighter + 0.05) / (darker + 0.05);
}

async function writeObservation(page, observation) {
  const screenshotPath = process.env.TS926_SCREENSHOT_PATH;
  const observationPath = process.env.TS926_OBSERVATION_PATH;

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }

  if (observationPath) {
    fs.mkdirSync(path.dirname(observationPath), { recursive: true });
    fs.writeFileSync(
        observationPath,
        `${JSON.stringify(observation, null, 2)}\n`,
        'utf-8',
    );
  }
}

test('axe-core treats an exact 4.5:1 text contrast boundary as compliant', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.setContent(`
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>TS-926 Boundary Contrast Probe</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: flex-start;
            justify-content: flex-start;
            background: #f4f6fb;
            color: #111827;
            font-family: Inter, Arial, sans-serif;
          }

          #boundary-card {
            margin: 24px;
            width: 360px;
            background: ${BACKGROUND_COLOR};
            border: 1px solid #d0d7e2;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            padding: 24px;
          }

          #boundary-text {
            margin: 0 0 16px 0;
            color: ${TEXT_COLOR};
            font-size: 16px;
            line-height: 24px;
          }

          #open-settings {
            border: 1px solid #1f2937;
            border-radius: 999px;
            background: #ffffff;
            color: #111827;
            font-size: 14px;
            line-height: 20px;
            padding: 10px 16px;
          }
        </style>
      </head>
      <body>
        <section id="boundary-card" aria-label="Contrast boundary card">
          <p id="boundary-text">${VISIBLE_TEXT}</p>
          <button id="open-settings" aria-label="${BUTTON_LABEL}">
            Open settings
          </button>
        </section>
      </body>
    </html>
  `);

  const boundaryText = page.locator('#boundary-text');
  const actionButton = page.getByRole('button', { name: BUTTON_LABEL });

  await expect(boundaryText).toBeVisible();
  await expect(boundaryText).toHaveText(VISIBLE_TEXT);
  await expect(actionButton).toBeVisible();

  const observation = await page.evaluate(() => {
    function parseCssColor(value) {
      const match = value.match(/rgba?\(([^)]+)\)/i);
      if (!match) {
        throw new Error(`Unsupported CSS color: ${value}`);
      }

      const channels = match[1].split(',').map((entry) => Number(entry.trim()));
      const [red, green, blue, alpha = 1] = channels;
      return { red, green, blue, alpha };
    }

    function compositeColor(foreground, background) {
      const alpha = foreground.alpha;
      return {
        red: foreground.red * alpha + background.red * (1 - alpha),
        green: foreground.green * alpha + background.green * (1 - alpha),
        blue: foreground.blue * alpha + background.blue * (1 - alpha),
      };
    }

    function normalizeSrgb(channel) {
      const normalized = channel / 255;
      return normalized <= 0.04045
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    }

    function relativeLuminance(color) {
      return (
        0.2126 * normalizeSrgb(color.red) +
        0.7152 * normalizeSrgb(color.green) +
        0.0722 * normalizeSrgb(color.blue)
      );
    }

    function contrastRatio(foreground, background) {
      const lighter = Math.max(
          relativeLuminance(foreground),
          relativeLuminance(background),
      );
      const darker = Math.min(
          relativeLuminance(foreground),
          relativeLuminance(background),
      );
      return (lighter + 0.05) / (darker + 0.05);
    }

    const textNode = document.getElementById('boundary-text');
    const buttonNode = document.getElementById('open-settings');
    const cardNode = document.getElementById('boundary-card');
    if (!textNode || !buttonNode || !cardNode) {
      throw new Error('TS-926 probe nodes were not rendered.');
    }

    const textStyle = window.getComputedStyle(textNode);
    const cardStyle = window.getComputedStyle(cardNode);
    const foreground = parseCssColor(textStyle.color);
    const background = parseCssColor(cardStyle.backgroundColor);
    const effectiveForeground = foreground.alpha < 1
      ? compositeColor(foreground, background)
      : foreground;

    return {
      title: document.title,
      visibleText: textNode.textContent.trim(),
      buttonText: buttonNode.textContent.replace(/\s+/g, ' ').trim(),
      buttonAriaLabel: buttonNode.getAttribute('aria-label'),
      renderedForeground: textStyle.color,
      renderedBackground: cardStyle.backgroundColor,
      effectiveForegroundRgb: {
        red: Number(effectiveForeground.red.toFixed(4)),
        green: Number(effectiveForeground.green.toFixed(4)),
        blue: Number(effectiveForeground.blue.toFixed(4)),
      },
      contrastRatio: Number(
          contrastRatio(effectiveForeground, background).toFixed(4),
      ),
    };
  });

  await writeObservation(page, observation);

  const violations = await collectAccessibilityViolations(page);

  expect(observation.title).toBe('TS-926 Boundary Contrast Probe');
  expect(observation.visibleText).toBe(VISIBLE_TEXT);
  expect(observation.buttonAriaLabel).toBe(BUTTON_LABEL);
  expect(observation.contrastRatio).toBeGreaterThanOrEqual(4.5);
  expect(Math.abs(observation.contrastRatio - 4.5)).toBeLessThanOrEqual(0.01);
  expect(violations, formatViolations(violations)).toEqual([]);
});
