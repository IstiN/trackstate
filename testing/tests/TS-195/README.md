# TS-195

Validates that archiving an existing issue relocates the full issue directory,
including non-markdown artifacts, from active storage into archive storage.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122` plus sibling
   `attachment.txt`
2. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
3. verify the active issue directory no longer contains `main.md` or
   `attachment.txt`
4. verify archive storage contains both relocated artifacts under
   `TRACK/.trackstate/archive/TRACK-122/`
5. verify the archived issue remains searchable, resolves to the archived path,
   and the archive workflow commits the expected repository change

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-195/test_ts_195.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
