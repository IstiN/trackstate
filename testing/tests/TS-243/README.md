# TS-243

Validates that after triggering concurrent delete operations, the repository can be reloaded
successfully without Git 'path does not exist' errors and that search queries remain functional.

The automation covers the ticket against a temporary local Git-backed TrackState repository:
1. Seeds a clean repository with three active delete targets, one surviving issue, and initial state
2. Verifies all issues are visible in search before the concurrent delete workflow
3. Invokes concurrent `deleteIssue` calls for multiple issues through the repository service
4. Reloads the repository (which should not fail with Git path-not-found errors)
5. Executes a search query (`project = TRACK`) and verifies it returns only the surviving issue
6. Confirms deleted issues are no longer searchable
7. Verifies the repository index no longer references deleted issues

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-243/test_ts_243.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
