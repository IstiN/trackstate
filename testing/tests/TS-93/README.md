# TS-93

Validates that a dirty local save failure is surfaced promptly and that the app
remains responsive afterward in Local Git mode.

The automation:
1. creates a temporary local Git fixture and dirties `DEMO/DEMO-1/main.md`
2. edits the same issue description through the real `TrackStateApp` UI
3. verifies the visible save-failure guidance includes `commit`, `stash`, and
   `clean`
4. attempts to dismiss that specific failed-save banner before continuing
5. verifies the UI can still search for and open `DEMO-2`

This ticket intentionally stays product-facing: if the dirty-save banner has no
real dismiss control, the test remains failed to document the app gap instead
of masking it with a synthetic pass.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-93/dirty_local_save_ui_responsiveness_test.dart --reporter expanded
```

## Required environment and config

- Flutter 3.35.3 available on `PATH`
- No extra environment variables are required

## Current expected result

```text
The test passes only when the dirty-save error exposes a dismiss action on the
actual visible banner and the UI still remains responsive after that failure.
```
