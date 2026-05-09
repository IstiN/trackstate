# TS-135

Validates that the repository service can archive `TRACK-555`, persist the
archived lifecycle state in repository metadata, and expose that archived state
through a standard repository search.

The automation uses a temporary local Git-backed TrackState repository and
checks the scenario in two phases:
1. verify `TRACK-555` starts active and discoverable through standard search
2. invoke `archiveIssue` through the repository service, then verify the issue,
   repository index metadata, issue frontmatter, and standard search all report
   the archived lifecycle state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-135/test_ts_135.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
