# TS-497

Validates that the issue-detail **Attachments** UI stays honest when a project
uses `github-releases` attachment storage but the current hosted session cannot
perform release-backed uploads.

The scenario:

1. opens the production issue-detail surface for `TRACK-12`,
2. switches to the **Attachments** tab,
3. verifies the restriction notice stays inline and keeps upload actions
   unavailable,
4. confirms an existing release-backed attachment still exposes download, and
5. opens **Project Settings** to verify repository access still communicates the
   release-backed upload limitation.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-497/test_ts_497.dart
```

## Required environment

- Flutter SDK available on `PATH`
- No extra environment variables are required; the test uses widget fixtures and
  mock shared preferences

## Expected passing output

```text
00:00 +0: loading .../testing/tests/TS-497/test_ts_497.dart
00:00 +1: All tests passed!
```
