# TS-152

Validates that calling `archiveIssue` for an issue that is already archived
does not throw and preserves the archived lifecycle state across the Local Git
repository surfaces an integrated client can observe.

The automation uses a temporary local Git-backed TrackState repository and
checks the scenario in two phases:
1. verify `TRACK-555` starts archived in frontmatter, repository metadata, and
   standard repository search
2. invoke `archiveIssue` through the repository service again, then verify the
   issue stays archived without duplicate `archived: true` metadata and remains
   discoverable through standard search

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-152/test_ts_152.dart --reporter expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
