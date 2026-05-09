# TS-217

Validates that archiving an existing issue relocates its physical artifacts into
archive storage and updates the issue metadata to the archived state.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`, `main.md`, and sibling
   `attachment.txt`
2. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
3. verify the returned issue and reloaded repository state both report
   `archived: true`
4. verify the former active storage path no longer contains the issue artifacts
5. verify archive storage contains the relocated markdown and sibling artifact,
   preserves their contents, and remains visible through repository search

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-217/test_ts_217.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
