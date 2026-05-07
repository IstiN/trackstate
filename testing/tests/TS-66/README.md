# TS-66

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-66/test_ts_66.dart -r expanded
```

## Environment / config

No external credentials are required. The test creates a temporary local Git repository with active issues `TRACK-122` and `TRACK-123`, verifies the pre-delete state through the app's repository service, and then attempts to exercise the repository service delete path for `TRACK-123`.

If the product still does not expose a real delete API, the test fails explicitly instead of fabricating tombstone artifacts inside the fixture.

## Current blocked output

```text
Bad state: TS-66 requires a real repository-service delete operation, but LocalTrackStateRepository does not expose deleteIssue for TRACK-123. The current repository API only supports loadSnapshot, searchIssues, connect, and updateIssueStatus.
```
