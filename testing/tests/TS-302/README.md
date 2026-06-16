# TS-302

Validates that creating a child issue from the Hierarchy view pre-fills the
visible parent relationship metadata for both epic and story source rows.

The automation:
1. creates a disposable Local Git repository with epic `TRACK-1` and child
   story `TRACK-2`
2. launches the real `TrackStateApp` in Local Git mode and opens `Hierarchy`
3. triggers the row-level `Create child issue` action for `TRACK-1`
4. verifies the visible `Create issue` form shows `Issue Type = Story`,
   `Epic = TRACK-1 · Hierarchy parent epic`, and user-facing controls for
   `Summary`, `Description`, `Save`, and `Cancel`
5. triggers the same action for `TRACK-2`
6. verifies the visible `Create issue` form shows `Issue Type = Sub-task`,
   `Parent = TRACK-2 · Hierarchy child story`, and the derived
   `Epic = TRACK-1 · Hierarchy parent epic`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-302/test_ts_302.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Hierarchy child-create action opens the Create issue dialog with the
correct issue type and relationship metadata prefilled for both epic-to-story
and story-to-sub-task flows.

Fail: the Hierarchy row action is missing, the Create issue dialog does not
open, the visible Issue Type/Epic/Parent values are incorrect, or the expected
user-facing controls are absent.
```
