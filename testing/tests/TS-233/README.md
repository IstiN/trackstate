# TS-233

Validates that Local Git issue creation enforces the required `Summary` field
from the Dashboard top-bar `Create issue` flow.

The automation:
1. creates a temporary Local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Dashboard` and verifies the top bar exposes a visible `Create issue`
   control
4. opens the create form, keeps `Summary` empty, enters
   `Mandatory field check` into `Description`, and clicks `Save`
5. verifies a visible summary-required validation message is shown and the form
   stays open with `Summary` still empty and `Description` preserved
6. verifies the Local Git storage layer is unchanged (no new issue key,
   `DEMO/DEMO-2/main.md` not created, no commit, clean worktree)

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-233/test_ts_233.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: saving with an empty Summary shows a visible summary-required validation
message, keeps the create form open, and does not create a new Local Git issue.

Fail: the Dashboard top-bar Create issue control is missing/unreachable, save is
accepted without Summary, validation feedback is missing, or Local Git storage
changes after submission.
```
