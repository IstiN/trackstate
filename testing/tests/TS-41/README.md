# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The automation covers the ticket in two layers against the same dirty local
issue:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact description write through the provider-backed save path
4. launch the real `TrackStateApp`, open `DEMO-1`, try to edit the description,
   click `Save`, and verify visible `commit` / `stash` / `clean` guidance

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
Once TS-41 is fixed, both tests pass:
- the provider-backed dirty-write failure becomes actionable
- the real issue-detail save flow surfaces visible commit/stash/clean guidance
```
