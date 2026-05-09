# TS-104

## Install dependencies

```bash
flutter pub get
```

If the Flutter SDK is not already on your `PATH`, export it first:

```bash
export PATH="<flutter-sdk>/bin:$PATH"
```

## Run this test

```bash
flutter test testing/tests/TS-104/test_ts_104.dart
```

## Environment requirements

- No additional environment variables are required.
- The test uses a provider-backed widget fixture that starts writable and then
  downgrades the live session to read-only without reopening the issue detail.

## Expected passing output

The test passes when the open issue detail continues showing the selected issue
while the same live session transitions from write-enabled to read-only, and the
UI immediately disables or hides write actions plus renders the scoped
read-only explanation banner without a manual refresh.
