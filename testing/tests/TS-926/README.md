# TS-926

## Objective

Verify that the Playwright + axe-core accessibility runner treats an exact
WCAG AA text contrast boundary of 4.5:1 as compliant.

## Automation approach

1. Render a minimal probe page with visible text at an effective 4.5:1 contrast
   ratio on a white background.
2. Reuse the shared `testing/accessibility/accessibility_gate.js` helper that
   the CI accessibility workflow uses.
3. Confirm the rendered probe stays free of `color-contrast` and
   `non-descriptive-label` violations and that the Playwright run exits
   successfully.
