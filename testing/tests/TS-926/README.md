# TS-926

## Objective

Verify that the live PR-triggered GitHub Actions accessibility workflow treats
an exact WCAG AA text contrast boundary of 4.5:1 as compliant.

## Automation approach

1. Create a disposable PR that injects a reusable Flutter probe surface with a
   fixed exact-boundary color pair and descriptive button text into the app
   entrypoint.
2. Wait for the real pull-request GitHub Actions workflow to complete on that
   disposable branch.
3. Inspect the hosted PR checks surface plus the workflow jobs, steps, and
   Playwright accessibility logs to confirm the compliant boundary probe passes
   without `color-contrast` or `non-descriptive-label` violations.
