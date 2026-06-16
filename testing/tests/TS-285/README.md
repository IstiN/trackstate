# TS-285

Validates the optimistic concurrency contract for `IssueMutationService.updateFields`
when the issue revision becomes stale after the service reads the file but before
the provider applies the write.

The production service does not take an explicit `expectedRevision` parameter, so
this automation reproduces the stale revision condition against the live
implementation by:
1. seeding a clean Local Git-backed repository with active issue `TRACK-122`
2. calling `IssueMutationService.updateFields` for that issue
3. injecting a real concurrent Git commit between the initial read and the write
   revision check
4. verifying the returned typed failure result reports a `conflict` and exposes
   the current revision in machine-readable form while the user-visible issue
   state remains on the concurrent version

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-285/test_ts_285.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
