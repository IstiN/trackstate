# TS-103

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
flutter test testing/tests/TS-103/test_ts_103.dart
```

## Environment requirements

- No additional environment variables are required.
- The test uses the built-in demo issue snapshot and a writable provider-backed repository fixture.

## Expected passing output

The test passes when the issue detail screen opens TRACK-12 in a write-enabled
session, shows the user-facing issue content, exposes enabled Edit, Transition,
and Comments actions, and does not render any read-only explanation or
permission-required guidance.
