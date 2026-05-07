# TS-41

Validates the TS-41 dirty-write behavior for `DEMO/DEMO-1/main.md`.

The automation covers the exact write path and a real TrackState issue-detail flow probe:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact provider-backed description write path
4. open the same issue in the real `TrackStateApp`, attempt the issue-detail description edit/save flow, and assert the visible recovery guidance if the UI exposes it

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
The provider-backed description save and the real issue-detail save flow both
pass once TrackState exposes the edit/save controls in the app and the
dirty-write failure tells the user to commit, stash, or clean local changes
first.
```
