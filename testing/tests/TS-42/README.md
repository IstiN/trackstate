# TS-42

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
flutter test testing/tests/TS-42/test_ts_42.dart
```

## Environment requirements

- No additional environment variables are required.
- The test uses the shared read-only and writable issue-detail fixtures.
- The scenario opens issue `TRACK-12` through the supported search flow and
  compares a writable baseline with a read-only `canWrite=false` session.

## Expected passing output

The test passes when the issue detail screen guards write actions up front for a
read-only session. `Transition`, `Edit`, and `Comment` must be disabled or
hidden when `canWrite=false`, and a visible permission/read-only explanation
must be present. The test also checks the writable baseline so it only treats an
action as capability-guarded if the same control is exposed and enabled when
`canWrite=true`.
