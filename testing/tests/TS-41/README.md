# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The automation covers the ticket in two layers against the same dirty local
issue:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact description write through the provider-backed save path

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
Current coverage stays on the real local Git write path for DEMO-1/main.md.
The test passes only once the provider-backed dirty-write failure becomes
actionable and tells the user to commit, stash, or clean local changes first.
```
