# TS-303

Validates create-issue hierarchy rules in Local Git mode.

The automation:
1. launches the real `TrackStateApp` with a Local Git repository fixture that
   contains Epic, Story, and Sub-task issue types
2. opens `Dashboard` and starts the top-bar `Create issue` flow
3. switches the issue type to `Epic` and verifies `Parent` and `Epic` are hidden
4. switches the issue type to `Sub-task` and verifies `Parent` is shown while
   `Epic` becomes a read-only derived field
5. attempts to save without a parent and verifies the visible
   `Sub-tasks require a parent issue.` validation message
6. selects a parent story and verifies the read-only `Epic` field derives the
   parent story's epic value

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-303/test_ts_303.dart --reporter expanded
```

## Required configuration

This test creates its own temporary Local Git repository fixture, so no
external credentials or environment variables are required.

## Expected result

```text
Pass: Create issue hides Parent/Epic for Epic, requires Parent for Sub-task,
and derives a read-only Epic from the selected Parent.

Fail: Epic still shows hierarchy fields, Sub-task does not require Parent, or
Epic stays editable / fails to derive from the chosen Parent.
```
