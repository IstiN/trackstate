# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the current local-Git behavior in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. a real `TrackStateApp` widget attempt that dirties the same file, opens `DEMO-1`, edits the description, clicks `Save`, and waits for visible `commit` / `stash` / `clean` guidance

The second check uses the live app UI rather than a synthetic harness or source-file assertion. In the current checkout it still fails because the issue detail does not expose a description editor plus `Save`, and the provider message is still non-actionable.

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
0 passed, 2 failed
```
