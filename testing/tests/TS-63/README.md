# TS-63

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-63/test_ts_63.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository fixture and resolves the issue through the repository service, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
