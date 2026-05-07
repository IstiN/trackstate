# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the real local-Git path in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. a source-backed guard that documents the current issue-detail implementation still renders the description read-only with no `Save` action

The secondary check documents the current blocker for the ticketed UI flow: `lib/ui/features/tracker/views/trackstate_app.dart` still renders `Text(issue.description)` and exposes `Transition`, not an issue-detail `Save` action.

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

## Current expected result

```text
1 passed, 1 failed
```
