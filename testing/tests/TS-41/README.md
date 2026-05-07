# TS-41

Validates the TS-41 dirty-write behavior for `DEMO/DEMO-1/main.md`.

The automation covers the exact provider-backed write path and the live app
issue-detail save flow:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact provider-backed description write path
4. open the same issue in the real `TrackStateApp`
5. attempt the in-app description edit and `Save` flow
6. verify the rendered recovery guidance mentions `commit`, `stash`, and
   `clean`

The ticket wiring follows the shared testing layers via reusable fixtures under
`testing/fixtures/` and shared app-screen abstractions.

The widget coverage uses the shared `TrackStateAppComponent` abstraction rather
than ticket-local widget access so the test stays within the documented
`tests -> components -> frameworks -> core` layering.

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
The test should pass once both the provider-backed write path and the real
issue-detail save flow surface actionable recovery guidance to commit, stash,
or clean local changes first.
```
