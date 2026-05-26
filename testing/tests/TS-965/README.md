# TS-965

## Objective

Verify that the live pull-request accessibility workflow fails when a rendered
Flutter probe uses alpha-blended text whose flattened contrast ratio falls below
WCAG AA 4.5:1.

## Automation approach

1. Create a disposable pull request that renders a probe using
   `colorScheme.onSurface.withAlpha(89)` on `colorScheme.surface` and keeps a
   descriptive semantics label so the scenario isolates contrast.
2. Resolve the current production light-theme colors from
   `lib/ui/core/trackstate_theme.dart` and calculate the flattened alpha-blended
   contrast ratio independently inside the test.
3. Wait for the live GitHub Actions pull-request workflow run, then inspect the
   contributor-visible status checks, jobs, logs, and run page.
4. Fail if the accessibility job stays green, if the run log lacks contrast
   failure evidence, or if the human-style GitHub Actions surface does not show
   the failing outcome.
