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

No external credentials are required. The test creates a temporary local Git repository with one active issue (`TRACK-122`) and one reserved deleted key (`TRACK-123`) represented in `TRACK/.trackstate/index/deleted.json`, then loads that repository through `LocalTrackStateRepository`.

The assertions verify that the deleted-key metadata is exposed through `snapshot.repositoryIndex.deleted`, that `TRACK-123` no longer resolves through the active repository index, and that standard search still returns only the surviving active issue.

## Expected passing output

```text
00:00 +1: All tests passed!
```
