# TS-97

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-97/test_ts_97.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository fixture and resolves the issue through the repository service, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
