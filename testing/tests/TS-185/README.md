# TS-185

Validates that archiving an existing issue with a real Git lock file present
surfaces a sanitized repository-domain exception instead of leaking raw Git CLI
details.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. create `.git/index.lock` inside the repository to reproduce a real Git lock
   failure
3. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
4. verify the caller receives a `TrackStateRepositoryException` without raw Git
   stderr or filesystem details
5. verify standard repository search still shows `TRACK-122` as active
6. verify the original worktree issue markdown stays unchanged and the failed
   archive does not leave a Git status entry for the original issue artifact

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-185/test_ts_185.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
