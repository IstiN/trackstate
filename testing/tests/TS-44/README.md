# TS-44

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-44/attachment_capability_check_test.dart -r expanded
```

## Required configuration

This test uses the reusable TS-44 fixture in `testing/fixtures/attachments/` to assemble the stubbed GitHub framework adapter below the test layer, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
