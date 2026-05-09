# TS-166

Validates that archiving `TRACK-555` persists the archived lifecycle state to
physical repository storage and that a fresh `LocalTrackStateRepository`
instance still resolves the issue as archived after restart.

The automation uses a temporary local Git-backed TrackState repository fixture
and checks the scenario in two phases:
1. invoke `archiveIssue` and confirm the current repository session reports
   `TRACK-555` as archived in the returned issue, refreshed snapshot, search
   results, and persisted frontmatter
2. create a fresh repository instance against the same data directory and
   verify the reloaded issue, repository index, search results, and frontmatter
   still expose the archived state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-166/test_ts_166.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
