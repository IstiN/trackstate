# TS-447

Verifies that post-auth startup recovery performs exactly one automatic bootstrap resume and falls back to an explicit Retry flow after a resumed load is rate-limited again.

## Install dependencies

```bash
flutter pub get
```

## Run

```bash
flutter test testing/tests/TS-447/test_ts_447.dart --reporter expanded
```

## Environment

No additional environment variables are required.

## Expected passing output

```text
+1: All tests passed!
```
