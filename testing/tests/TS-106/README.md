# TS-106

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
flutter test testing/tests/TS-106/test_ts_106.dart
```

## Environment / config

No external environment variables are required. The test creates a temporary
local Git repository with a `Local User` author to satisfy the ticket
precondition, then launches the hosted runtime with a stored remote session
token backed by a mocked GitHub repository/user.

## Expected passing output

The Flutter test runner reports:

```text
All tests passed!
```
