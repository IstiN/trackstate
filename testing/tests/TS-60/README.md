# TS-60

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-60/test_ts_60.dart -r expanded
```

## Required configuration

This test reuses the shared attachment upload probe and a TS-60-specific fixture in `testing/fixtures/attachments/` to verify that a standard non-LFS file is uploaded through the GitHub Contents API, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
