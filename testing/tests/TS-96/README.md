# TS-96

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-96/test_ts_96.dart -r expanded
```

## Required configuration

This test uses a ticket-specific local Git repository fixture and resolves the
issue through `LocalTrackStateRepository` plus the shared
`IssueResolutionService`. It does not require live external credentials.

## Expected passing output

```text
00:00 +1: All tests passed!
```
