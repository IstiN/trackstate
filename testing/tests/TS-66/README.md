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

No external credentials are required. The test creates a temporary local Git repository with active issues `TRACK-122` and `TRACK-123`, deletes `TRACK-123` from the real repository file state with `git rm`, persists `.trackstate/tombstones/TRACK-123.json` plus `.trackstate/index/tombstones.json` through the app's local Git provider, and then confirms standard JQL search no longer returns the deleted issue.

## Expected passing output

```text
00:00 +1: All tests passed!
```
