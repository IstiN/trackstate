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

No external credentials are required. The test creates a temporary local Git repository with active issues `TRACK-122` and `TRACK-123`, executes the delete transition for `TRACK-123` inside the fixture, and then verifies `TRACK/.trackstate/index/deleted.json` reserves the deleted key while standard JQL search no longer returns it.

## Expected passing output

```text
00:00 +1: All tests passed!
```
