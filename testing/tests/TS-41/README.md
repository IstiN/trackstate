# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The automation currently keeps the valid provider-backed check on the same dirty
local issue:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact description write through the provider-backed save path

The current product surface in this checkout still renders the issue detail
description read-only and exposes no description-save action, so this ticket
automation cannot yet drive the requested in-app save flow from the UI.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-41/test_save_issue_with_dirty_local_files_test.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Current expected result

```text
The provider-backed assertion fails until the dirty-write message becomes
actionable and tells the user to commit, stash, or clean local changes first.
```
