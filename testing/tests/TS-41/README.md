# TS-41

Validates the TS-41 dirty-write behavior for `DEMO/DEMO-1/main.md`.

The automation covers the exact provider-backed write path and the live app
surface that exist in this checkout:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact provider-backed description write path

The ticket wiring follows the shared testing layers via reusable fixtures under
`testing/fixtures/` and shared app-screen abstractions.

The widget coverage opens the same local issue in the real `TrackStateApp` and
asserts the current issue-detail surface still renders the description while
exposing no `Edit` / `Save` action for that field.

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
The provider-backed dirty-write assertion still fails until the product error
message tells the user to commit, stash, or clean local changes first. The live
app-surface probe should pass and confirm the current checkout is still read
only for issue descriptions.
```
