# TS-41

Validates the real dirty-file save guard around `DEMO/DEMO-1/main.md`.

The TS-41 automation keeps the real dirty-write assertion live:
1. a provider-backed description save attempt against the dirty `main.md`

The real `TrackStateApp` detail view is still read-only in this branch and on `main`, so the ticket's in-app description Save flow remains explicitly skipped rather than replaced with a synthetic Save control or a board-move substitute.

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
00:00 +0 -1 ~1: The provider-backed dirty-save assertion still reports the AC3 product gap, and the real-app description flow stays skipped until the UI exists.
```
