# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the current local-Git behavior in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. a real `TrackStateApp` widget check that opens `DEMO-1` and verifies the issue detail still exposes `Transition`, not a description editor plus `Save`

The second check uses the live app UI rather than a synthetic harness or source-file assertion. It documents the current blocker for the ticketed flow: the issue detail is still read-only in local Git mode.

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

## Current expected result

```text
1 passed, 1 failed
```
