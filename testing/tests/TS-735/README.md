# TS-735

Validates the production inline pending banner that appears when a workspace
refresh is queued while the **Edit issue** dialog is still open.

The automation:
1. opens `TRACK-12` in the hosted write-enabled fixture reused from `TS-714`
2. starts an unsaved Description edit so the dialog stays in an active edit
   session
3. triggers an external background refresh and waits for the queued-update state
4. verifies the inline pending banner is visible inside the edit surface, keeps
   the user draft intact, and exposes a meaningful semantics label
5. checks the banner text contrast against WCAG AA, confirms the rendered
   colors match the TrackState design tokens, and confirms the banner text uses
   the expected body-small typography token

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-735/test_ts_735.dart --reporter expanded
```

## Expected result

```text
Pass: while edits are still open, the queued-refresh inline banner is visibly
rendered inside the Edit issue surface, preserves the user's draft, exposes a
meaningful semantics label for screen readers, and keeps the rendered banner
colors and typography aligned with the TrackState design tokens at 4.5:1 or
better text contrast.

Fail: the pending banner never appears, appears outside the edit surface,
replaces the draft, lacks meaningful semantics, or renders off-token colors or
sub-AA text contrast.
```
