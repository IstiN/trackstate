# TS-64

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-64/test_ts_64.dart -r expanded
```

## Required environment and config

- Flutter SDK 3.35.3 available at `/tmp/flutter/bin/flutter` or on `PATH`
- No extra environment variables are required
- The test creates a temporary local Git repository with a valid legacy index, moves `PROJECT-1` to `PROJECT/NEW-PARENT/PROJECT-1/`, rebuilds `.trackstate/index/issues.json` and `.trackstate/index/hierarchy.json`, and then verifies lookup by key through the rebuilt artifacts

## Expected passing output

```text
00:00 +1: All tests passed!
```
