# TS-41

Attempts the TS-41 dirty-write flow for `DEMO/DEMO-1/main.md` against the
current product surface in this checkout.

The automation covers the exact provider-backed write path and a live
`TrackStateApp` issue-detail attempt for the same dirty local issue:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact provider-backed description write path
4. open the same issue in the real `TrackStateApp`
5. attempt the issue-detail `Edit` / `Save` flow for that same dirty issue
6. verify the surfaced app message includes `commit`, `stash`, and `clean`

The executable failure signal remains the provider-backed save assertion: the
product still throws a non-actionable dirty-file message instead of telling the
user to `commit`, `stash`, or `clean` local changes first.

The widget case now establishes the same dirty-file precondition before opening
the app, so the UI attempt and provider assertion both target the same local
Git runtime state.

The ticket wiring follows the shared testing layers via reusable fixtures under
`testing/fixtures/` and the shared `TrackStateAppComponent` abstraction rather
than ticket-local widget access.

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
The provider-backed dirty-write assertion currently fails because the product
message still omits `commit` / `stash` / `clean`.
The widget attempt currently fails fast because the current issue detail does
not expose the required `Edit` / `Save` controls for the ticketed flow.
```
