# TS-499

Verifies the hosted Settings repository-access area remains accessible when
attachment support is fully available and when uploads are limited.

The automation:
1. launches the production Flutter app in hosted Settings with a remembered token
2. checks the visible repository-access status band, attachment callout, and
   token controls for both success and limited-storage states
3. verifies each callout exposes meaningful semantics, keeps screen-reader
   traversal ordered ahead of the token controls, and preserves logical keyboard
   Tab order through the form controls
4. measures the rendered text and icon contrast against the green or amber
   callout surfaces

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-499/test_ts_499.dart -r expanded
```

## Required environment / config

No external credentials are required. The test uses hosted repository fixtures
and mocked shared preferences inside the widget-test harness.

## Expected passing output

```text
00:00 +0: TS-499 access area accessibility keeps storage-aware messaging semantic, readable, and logically ordered
00:00 +1: All tests passed!
```
