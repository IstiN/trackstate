# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The TS-41 automation exercises the current local-Git behavior in two ways:
1. a provider-backed description save attempt against the dirty `main.md`
2. a real `TrackStateApp` widget attempt that dirties the same file, opens `DEMO-1`, edits the description, clicks `Save`, and expects visible `commit` / `stash` / `clean` recovery guidance

The second check now follows the ticketed UI flow directly and fails fast if the live issue-detail surface still does not expose the editor or `Save` control needed for that flow.

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
The exact result depends on the current product surface. On this branch the provider assertion still fails if the dirty-write message is non-actionable, and the widget check also fails if the live issue detail does not yet expose the editor/save flow.
```
