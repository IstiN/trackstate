# TS-43

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-43/local_git_identity_resolution_test.dart
```

## Environment / config

No external environment variables are required. The test creates a temporary local Git repository, configures `git user.name` and `git user.email`, and launches the app against that repository through the Local Git runtime.

## Expected passing output

The Flutter test runner reports:

```text
All tests passed!
```
