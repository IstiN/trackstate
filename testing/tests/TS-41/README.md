# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The current automation keeps coverage on the real local-Git write path that the
product exposes today:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the same description write through the provider-backed save path
4. assert that the resulting error includes `commit`, `stash`, and `clean`

This test does not claim in-app description edit-and-save coverage. The current
issue-detail UI still renders `issue.description` as read-only text and exposes
no `Save` action for description edits.

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
The provider-backed assertion fails until the dirty-write message becomes
actionable and tells the user to commit, stash, or clean local changes first.
```
