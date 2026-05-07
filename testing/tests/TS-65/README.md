# TS-65

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-65/test_ts_65.dart -r expanded
```

## Environment requirements

- No additional environment variables are required.
- The test uses a ticket-specific in-memory repository fixture that stores the stable status ID `in-progress` in `TRACK-65/main.md`.

## Expected passing output

```text
00:00 +1: All tests passed!
```
