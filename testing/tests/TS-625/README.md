# TS-625

Validates that stale `IssueMutationService.updateFields` saves surface a
machine-readable `conflict` category when the issue revision changes after the
caller reads it but before the mutation is written.

The production service does not accept a direct `expectedRevision` argument, so
this automation reproduces the stale revision scenario against the live
implementation by:
1. seeding a clean Local Git-backed repository with active issue `TRACK-122`
2. reading the current issue revision from the repository fixture
3. injecting a real concurrent Git commit before `updateFields` saves
4. verifying the returned failed mutation result reports the stable
   machine-readable `conflict` category while repository readers still see the
   winning concurrent state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-625/test_ts_625.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
