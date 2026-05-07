# TS-41

Validates the TS-41 dirty-write behavior for `DEMO/DEMO-1/main.md`.

The automation covers the same dirty local issue in two layers:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact provider-backed description write path
4. trigger the live TrackState board mutation path and assert the rendered
   tracker error banner contains the required recovery guidance

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
Current coverage stays on the real local Git mutation paths for DEMO-1/main.md.
The tests pass only once both the provider-backed dirty-write failure and the
live tracker banner tell the user to commit, stash, or clean local changes
first.
```
