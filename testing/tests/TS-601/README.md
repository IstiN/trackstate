# TS-601

Validates that `IssueMutationService.archiveIssue` allows archiving a parent
issue even when active child issues still exist.

The automation covers the production-visible flow by:
1. seeding a clean Local Git-backed repository with parent issue `EPIC-10` and
   child issue `TASK-20`
2. opening the repository through the shared `testing/` local Git repository
   port
3. invoking `archiveIssue('EPIC-10')` through the shared testing archive
   mutation service/driver layer
4. verifying the mutation succeeds, moves `EPIC-10` into archive storage, and
   persists `archived: true`
5. confirming `TASK-20` remains active, searchable, and still linked to
   `EPIC-10`

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-601/test_ts_601.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
