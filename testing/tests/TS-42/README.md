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
- The test uses the built-in demo issue snapshot and a read-only repository fake.

## Expected passing output

The test passes when the issue detail screen disables or hides write actions for
the read-only session and shows a visible read-only explanation, such as text or
tooltip that mentions permission, read-only mode, or write access.
