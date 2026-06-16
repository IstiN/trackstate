# TS-123

Validates that Local Git issue creation succeeds end to end when the repository
starts clean.

The automation:
1. creates a temporary clean Local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. locates a production-visible `Create issue` entry point from the primary UI
4. enters a summary and description, then submits the create action
5. verifies no dirty-repository failure banner appears
6. verifies the create form closes and the new issue is visible from the user's
   search/detail flow
7. verifies Local Git recorded a dedicated `Create DEMO-2` commit for the new
   issue file

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-123/test_ts_123.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: Local Git exposes a reachable Create issue flow, accepts the entered
details on a clean repository, closes the create form, shows the new issue in
the UI, and writes a dedicated Create DEMO-2 commit.

Fail: the create entry point is missing, submission surfaces a dirty-repository
warning or other error, the new issue is not visible to the user, or Local Git
does not record the expected commit.
```
