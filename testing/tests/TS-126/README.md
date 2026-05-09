# TS-126

Validates that an explicit `customFields` object and arbitrary top-level
frontmatter keys are merged into the same canonical `customFields` map.

The automation covers the ticket in two layers against the same temporary local
Git repository fixture:
1. resolve `DEMO-126` through the repository service and verify
   `customFields.explicit_key == "value1"` and
   `customFields.arbitrary_key == "value2"` while status/priority stay canonical
2. launch the real `TrackStateApp`, open the same issue, and verify the visible
   key, summary, description, status, and priority still render without errors

## Run this test

```bash
flutter test testing/tests/TS-126/test_ts_126.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```
