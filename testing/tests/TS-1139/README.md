# TS-1139

Validates that Create issue blocks Sub-task submission until a parent issue is selected.

The automation:
1. launches the real `TrackStateApp` in Local Git mode with the existing issue hierarchy fixture
2. opens the production `Create issue` flow
3. switches the issue type to `Sub-task`
4. leaves `Parent` empty while entering a valid `Summary`
5. attempts to submit and verifies the visible `Sub-tasks require a parent issue.` validation message
6. confirms the dialog stays open and no new issue is written to the repository

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-1139/test_ts_1139.dart --reporter expanded
```

## Required configuration

This test creates its own temporary Local Git repository fixture, so no
external credentials or environment variables are required.

## Expected result

```text
Pass: Create issue prevents saving a Sub-task without Parent, keeps the dialog
open, and shows the visible "Sub-tasks require a parent issue." validation.

Fail: The create flow submits without Parent, the validation message never
appears, or the repository writes a new Sub-task despite the missing parent.
```
