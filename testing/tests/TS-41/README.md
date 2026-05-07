# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the real local-Git path in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. the live `TrackStateApp` issue-detail flow: open the same issue, attempt to edit its description, click `Save`, and verify visible `commit` / `stash` / `clean` guidance

The widget case intentionally uses the real app surface instead of a synthetic save harness or a board-move substitute, so any failure comes from the actual UI path under test.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-41/test_save_issue_with_dirty_local_files_test.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected passing output

```text
00:00 +0: loading testing/tests/TS-41/test_save_issue_with_dirty_local_files_test.dart
00:00 +2: All tests passed!
```
