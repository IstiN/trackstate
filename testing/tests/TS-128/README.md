# TS-128

Validates that arbitrary top-level frontmatter keys with empty and explicit
`null` values are preserved in `customFields` and do not break the real
issue-detail flow.

The automation covers the ticket in two layers against the same temporary local
Git repository fixture:
1. resolve `DEMO-128` through the repository service and verify `empty_key` and
   `null_key` are preserved in `customFields` as `null` while canonical
   status/priority mappings stay intact
2. launch the real `TrackStateApp`, open the same issue, and verify the visible
   key, summary, description, status, and priority still render without errors

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-128/test_ts_128.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```
