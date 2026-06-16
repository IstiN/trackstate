# TS-67

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-67/test_ts_67.dart -r expanded
```

## Required configuration

This test uses a temporary Local Git repository fixture under `testing/fixtures/repositories/` and the shared Local Git repository service in `testing/components/services/`. No external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
