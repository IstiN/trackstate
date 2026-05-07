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

No external credentials are required. The test creates a temporary local Git repository with one active issue and one deleted issue represented in `TRACK/.trackstate/index/deleted.json`, then verifies the repository service keeps the deleted key reserved in tombstone metadata while standard JQL search no longer returns that issue.

## Expected passing output

```text
00:00 +1: All tests passed!
```
