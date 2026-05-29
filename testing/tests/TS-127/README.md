# TS-127

Validates that arbitrary top-level frontmatter keys preserve integer, boolean,
and list YAML data types inside `customFields`.

The automation covers the ticket in two layers against the same temporary local
Git repository fixture:
1. resolve `DEMO-127` through the repository service and verify `my_int`,
   `my_bool`, and `my_list` stay typed inside `customFields`
2. launch the real `TrackStateApp`, open the same issue, and verify the visible
   issue detail loads without framework errors

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-127/test_ts_127.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```
