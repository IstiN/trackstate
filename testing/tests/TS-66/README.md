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

No external credentials are required. The test creates a temporary local Git repository with active issues `TRACK-122` and `TRACK-123`, verifies the pre-delete state through the app's repository service, and then checks whether the current product repository service exposes the delete path TS-66 requires.

If the product still does not expose a real delete API, the fixture fails explicitly instead of probing unsupported runtime methods or fabricating tombstone artifacts inside the fixture.

## Current blocked output

```text
Bad state: TS-66 requires a real repository-service delete operation, but LocalTrackStateRepository does not expose deleteIssue for TRACK-123. The current repository API only supports loadSnapshot, searchIssues, connect, and updateIssueStatus.
```
