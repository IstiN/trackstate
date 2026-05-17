# TS-716

Verifies the hosted read-only workspace-sync error state in the production
Flutter UI, including the top-bar sync-pill semantics label, visible
`Attention needed` contrast, and keyboard focus order for the visible recovery
actions in **Settings > Workspace sync**.

The automation only passes when a user can reproduce the real error state and
observe:
1. descriptive sync-error semantics on the top-bar pill,
2. WCAG AA 4.5:1 contrast for the visible error-state label, and
3. keyboard Tab traversal that follows the rendered top-to-bottom order of
   **Retry** and **Reconnect for write access**.

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-716/test_ts_716.dart --reporter expanded
```

## Expected behavior

The test should exercise the real production-visible error state and either:
1. pass when semantics, contrast, and keyboard order all satisfy the ticket, or
2. fail with recorded evidence of the real product defect.
