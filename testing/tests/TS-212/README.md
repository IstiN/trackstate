# TS-212

Validates that archiving an existing issue succeeds even when the archive
directory is missing, and that the repository surfaces the relocated archived
path afterward.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. verify `TRACK/.trackstate/archive/` does not exist before archiving
3. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
4. verify `TRACK/.trackstate/archive/TRACK-122/main.md` is created and the
   active `TRACK/TRACK-122/main.md` artifact is removed
5. verify the reloaded repository index, current issue, and repository search
   all expose `TRACK-122` at the archived storage path

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-212/test_ts_212.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
