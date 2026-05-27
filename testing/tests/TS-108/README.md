# TS-108

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-108/test_ts_108.dart
```

## Environment / config

No external environment variables are required. The test launches the hosted-mode app without a stored OAuth token or Local Git repository and verifies the visible guest-state profile surface in the top bar.

## Expected passing output

The Flutter test runner reports:

```text
All tests passed!
```
