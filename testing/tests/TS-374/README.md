# TS-374

Validates that hosted read-only auth-gate surfaces stay accessible.

The automation:
1. launches the real TrackState app in a connected read-only hosted session
2. verifies the global repository-access banner exposes localized visible text
   and semantics, and that keyboard Tab navigation reaches its CTA
3. verifies the banner CTA exposes a distinct focused treatment with readable
   contrast and opens the reconnect dialog from the keyboard
4. opens an issue's Comments tab and verifies the inline auth-gate callout keeps
   its localized semantics, visible messaging, gated composer state, and WCAG AA
   text contrast

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-374/test_ts_374.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test stores a mock hosted token in `SharedPreferences` to drive the
  connected read-only provider session

## Expected result

```text
Pass: the read-only global banner and inline Comments callout expose localized
semantics, their CTAs are keyboard reachable, the global CTA has a distinct
focused visual treatment with readable contrast, and the Comments callout text
meets WCAG AA contrast.

Fail: either callout is missing, semantics labels are generic or absent, Tab
navigation cannot reach the banner CTA, the focused CTA treatment is visually
indistinct or unreadable, or the Comments callout text contrast drops below
4.5:1.
```
