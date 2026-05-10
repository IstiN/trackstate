# TS-283

Validates that `IssueMutationService.deleteIssue` refuses to delete a parent
issue while it still has active child issues, preventing the hierarchy from
being orphaned.

The automation covers the production-visible flow by:
1. seeding a clean Local Git-backed repository with parent issue `EPIC-10` and
   child issue `TASK-20`
2. calling `IssueMutationService.deleteIssue('EPIC-10')`
3. verifying the returned typed failure is `validation` with the exact
   user-facing message
4. confirming the blocked delete leaves issue files, tombstone state, repository
   metadata, search visibility, and hierarchy relationships unchanged

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-283/test_ts_283.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
