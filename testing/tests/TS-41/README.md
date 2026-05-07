# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the current local-Git behavior in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. a real `TrackStateApp` widget proof that dirties the same file, opens `DEMO-1`, and verifies the current local-Git issue detail still exposes no description editor or `Save` action

The second check uses the live app UI rather than a synthetic harness or source-file assertion. In the current checkout the issue detail is still read-only, so the provider-backed dirty-write assertion remains the single failing AC3 signal.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-41/test_save_issue_with_dirty_local_files_test.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Current expected result

```text
1 passed, 1 failed
```
