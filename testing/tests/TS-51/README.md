# TS-51

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-51/connected_interaction_contrast_test.dart -r expanded
```

## Required configuration

This test uses the existing Settings widget harness with a remembered GitHub token in mocked shared preferences, so no external credentials or runtime services are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
