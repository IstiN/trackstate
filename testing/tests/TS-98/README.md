# TS-98

Validates that malformed primitive `customFields` frontmatter does not crash
issue resolution and still leaves the real issue-detail flow usable.

The automation covers the ticket in two layers against the same temporary local
Git repository fixture:
1. resolve `DEMO-98` through the repository service and verify malformed
   `customFields` defaults to an empty map while status/priority stay canonical
2. launch the real `TrackStateApp`, open the same issue, and verify the visible
   key, summary, description, status, and priority still render without errors

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-98/test_ts_98.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```
