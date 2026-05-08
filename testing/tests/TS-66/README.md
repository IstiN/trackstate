# TS-66

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-66/test_ts_66.dart -r expanded
```

## Environment / config

No external credentials are required. The test creates a temporary local Git
repository where both `TRACK-122` and `TRACK-123` start as active issues.

TS-66 verifies that pre-delete state is real, then attempts to drive the delete
through the application repository service. The current product repository
contract still exposes only `loadSnapshot`, `searchIssues`, `connect`, and
`updateIssueStatus`, so the test fails explicitly until a real delete API is
available from `testing/` alone.

## Expected current output

```text
Bad state: TS-66 requires a real repository-service delete operation, but LocalTrackStateRepository does not expose deleteIssue for TRACK-123. The current repository API only supports loadSnapshot, searchIssues, connect, and updateIssueStatus.
```
