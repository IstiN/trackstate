# TS-218

Validates that a failed archive relocation leaves the Git worktree and index
clean and unchanged.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. pre-create `TRACK/.trackstate/archive` with restricted permissions so archive
   relocation fails on the real filesystem
3. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
4. verify the caller receives a `TrackStateRepositoryException`
5. verify `git status`, the staged index, and untracked files still match the
   pre-failure clean state and that integrated repository search still exposes
   `TRACK-122` as active at `TRACK/TRACK-122/main.md`

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-218/test_ts_218.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture and uses
real filesystem permissions to block archive relocation, so no external
credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
