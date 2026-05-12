# TS-456

Verifies that the deferred **Attachments** error state exposes an accessible
Retry action and keeps the rendered error treatment readable inside the issue
detail collaboration tabs.

The automation:
1. launches the production `TrackStateApp` with a provider-backed repository
   whose attachment hydration fails on every retry
2. opens the seeded issue detail and switches to the visible `Attachments` tab
3. waits for the production deferred-load error card to render
4. verifies the visible error copy, exact `Retry` semantics label, and
   deferred error icon semantics label
5. tabs through the rendered issue detail until `Retry` receives keyboard focus,
   then activates it with `Enter`
6. verifies the retry action re-attempts the deferred attachment read
7. asserts the deferred error card keeps the expected `surfaceAlt` / AC5
   styling contract, then measures the rendered error-card text and error-icon
   contrast against that surface

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-456/test_ts_456.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: the Attachments deferred error state renders visible retry copy, exposes a
meaningful Retry semantics label and deferred error icon semantics label, is
reachable and activatable by keyboard, and keeps its rendered error treatment at
WCAG AA contrast.

Fail: the error state is missing, Retry is not exposed with an accessible label
or keyboard activation path, the deferred error icon is missing or not labeled
for assistive technology, or the rendered error treatment misses the required
contrast threshold.
```
