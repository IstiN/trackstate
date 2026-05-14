# TS-714

Validates that background sync does not overwrite an unsaved Description draft,
surfaces the visible `Updates pending` state while the issue edit dialog remains
open, and applies the queued refresh only after the user saves.

The automation:
1. opens `TRACK-12` in a connected hosted session backed by a mutable repository
   fixture
2. verifies the existing Description is loaded into the production issue editor
3. enters an unsaved local Description draft
4. simulates an external Git change to the same issue while editing is still in
   progress
5. verifies the visible `Updates pending` top-bar state and deferred-refresh
   helper copy appear without replacing the local draft
6. saves the draft and verifies the pending state clears while the saved draft
   remains visible instead of the remote background value

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-714/test_ts_714.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the issue editor keeps the unsaved Description draft after a background
change is detected, the UI shows `Updates pending` plus the deferred-refresh
message during editing, and saving clears the pending state while preserving the
user's saved draft.

Fail: the background refresh overwrites the draft, the pending indicator or
helper message never appears, or saving leaves the queued refresh stuck or
replaces the saved draft with the remote background change.
```
