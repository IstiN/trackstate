# TS-154

Validates that `LocalTrackStateRepository` fully exposes the required
repository lifecycle contract at runtime and that `archiveIssue` executes
through the regression path that previously failed with `NoSuchMethodError`.

The automation uses a temporary local Git-backed TrackState repository fixture
and checks the scenario in three phases:
1. instantiate `LocalTrackStateRepository` under the real repository contract
2. verify every required runtime lifecycle method is present and callable
3. invoke `archiveIssue`, then confirm the archived state is persisted in the
   resolved issue, repository index metadata, issue frontmatter, and standard
   repository search results

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-154/test_ts_154.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
