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

No external credentials are required. The test creates a temporary local Git
repository where both `TRACK-122` and `TRACK-123` start as active issues.

TS-66 verifies that pre-delete state is real, then attempts to drive the delete
through the application repository service, verifies the tombstone artifact at
`.trackstate/tombstones/TRACK-123.json`, checks the reserved-key index at
`.trackstate/index/tombstones.json`, and confirms that normal search results no
longer include the deleted issue.

## Expected current output

```text
00:00 +1: All tests passed!
```
