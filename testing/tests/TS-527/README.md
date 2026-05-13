# TS-527

Verifies that mixed legacy and release-backed attachment history does not hide
the visible upload controls for adding a new file in the production
**Attachments** tab.

The automation:
1. launches the production `TrackStateApp` with a remembered hosted token, write
   access, and `attachmentStorage.mode = github-releases`
2. seeds `TRACK-12` with one visible `repository-path` attachment row and one
   visible `github-releases` attachment row
3. opens the seeded issue detail and switches to the **Attachments** tab
4. verifies **Choose attachment** stays visible and enabled while
   **Upload attachment** stays visible and disabled before selection
5. selects a unique file through the production upload action, uploads it, and
   verifies the new row is persisted on the `github-releases` backend

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-527/test_ts_527.dart --reporter expanded
```

## Required environment / config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses hosted repository fixtures, mocked shared preferences, and an
  injected attachment picker inside the widget test harness

## Expected result

```text
Pass: the mixed-backend Attachments tab keeps the upload controls available,
selecting a file enables Upload attachment, and the persisted new attachment
entry uses storageBackend = github-releases.

Fail: either upload control is missing or disabled for the write-enabled hosted
session, choosing a file does not enable Upload attachment, or the persisted
attachment metadata does not stay on github-releases storage.
```
