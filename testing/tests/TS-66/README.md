# TS-66

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-66/test_ts_66.dart -r expanded
```

## Environment / config

No external credentials are required. The test creates a temporary local Git repository with active issues `TRACK-122` and `TRACK-123`, verifies the pre-delete state through the app's repository service, and then attempts the real repository-service delete step for `TRACK-123`.

The current branch is blocked in product code: `TrackStateRepository` / `LocalTrackStateRepository` still exposes `loadSnapshot`, `searchIssues`, `connect`, and `updateIssueStatus`, but no delete operation. TS-66 therefore fails explicitly instead of fabricating tombstone artifacts inside `testing/`.

## Current expected output

```text
Bad state: TS-66 requires a real repository-service delete operation, but LocalTrackStateRepository does not expose deleteIssue for TRACK-123. The current repository API only supports loadSnapshot, searchIssues, connect, and updateIssueStatus.
```
