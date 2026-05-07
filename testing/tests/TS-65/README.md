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
- The test uses a ticket-specific in-memory repository fixture that stores the custom stable status ID `wip` in `TRACK-65/main.md` and resolves it through `config/statuses.json`.

## Expected passing output

```text
00:00 +1: All tests passed!
```
