# TS-41

Validates the TS-41 dirty-save behavior for `DEMO/DEMO-1/main.md`.

The automation now keeps two linked checks on the same dirty local issue:
1. create a temporary local Git runtime fixture
2. dirty `DEMO/DEMO-1/main.md` outside TrackState
3. attempt the exact description write through the provider-backed save path
4. drive the real `TrackStateApp` board mutation flow and assert the rendered
   failure banner for that dirty issue contains `commit`, `stash`, and `clean`

The product still does not expose an in-app description editor on the issue
detail screen in this checkout, so the provider-backed save check pins the exact
`main.md` write path while the widget check validates the live app notification
surface that users see for dirty-write failures.

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
Both assertions fail until the dirty-write message becomes actionable and tells
the user to commit, stash, or clean local changes first.
```
