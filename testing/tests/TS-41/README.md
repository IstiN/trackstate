# TS-41

Validates that TrackState blocks mutations when `DEMO/DEMO-1/main.md` has local dirty changes.

The TS-41 automation keeps two checks in sync with AC3:
1. a provider-backed description save attempt against the dirty `main.md`
2. a real `TrackStateApp` widget flow that triggers a user-visible failure banner after a board move hits the same dirty file

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
00:00 +2: All tests passed!
```
