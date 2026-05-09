# TS-112

Validates that the Local Git dirty-save error banner remains visible until the
user dismisses it manually.

The automation:
1. creates a temporary local Git fixture and dirties `DEMO/DEMO-1/main.md`
2. edits the same issue description through the real `TrackStateApp` UI
3. triggers the visible `Save failed:` banner with `commit` / `stash` / `clean`
   recovery guidance
4. waits 10 seconds without interacting and verifies the banner is still visible
5. dismisses the banner through its visible close affordance and verifies it
   clears from the screen

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-112/test_ts_112.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit SDK path in your CI

## Current expected result

```text
The test passes only when the dirty-save notification stays visible for the full
10-second observation window and disappears only after the user explicitly
dismisses it.
```
