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

No external credentials are required. The test creates a temporary local Git repository with two revisions:

1. an active revision where both `TRACK-122` and `TRACK-123` exist as issue files
2. a follow-up revision where `TRACK-123` is removed and its deleted-key metadata is written to `TRACK/.trackstate/index/deleted.json`

TS-66 loads both revisions through `LocalTrackStateRepository` and verifies the behavior currently shipped on `origin/main`: deleted keys are hydrated from `.trackstate/index/deleted.json`, excluded from active search results, and preserved in `snapshot.repositoryIndex.deleted`.

## Expected passing output

```text
00:00 +1: All tests passed!
```
