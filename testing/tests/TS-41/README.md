# TS-41

Validates that TrackState blocks mutations when `DEMO/DEMO-1/main.md` has local dirty changes.

The current app surface in this repository still renders issue descriptions read-only, so this ticket automation stays on the real local Git adapter path and does not invent a synthetic Save UI.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-41/test_save_issue_with_dirty_local_files_test.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected passing output

```text
00:00 +1: All tests passed!
```
