# TS-399

Validates that changing **Story-A** from **Epic-1** to **Epic-2** does not save
immediately when the change would relocate a subtree, and that the confirmation
dialog shows a user-facing summary of the affected hierarchy move.

The automation:
1. seeds a local Git-backed hierarchy with `STORY-A` under `EPIC-1` and exactly
   three descendant sub-tasks
2. opens the production **Edit** surface for `STORY-A`
3. changes the visible **Epic** field from `EPIC-1` to `EPIC-2`
4. clicks **Save** and verifies the save is blocked behind a confirmation dialog
5. checks the dialog summary for the moved issue, the three descendants, and the
   destination epic before any move is confirmed

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-399/test_ts_399.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own local Git repository fixture

## Expected result

```text
Pass: Saving after changing Story-A from Epic-1 to Epic-2 opens a confirmation
dialog before any move is applied, and the visible summary identifies Story-A,
its 3 descendants, and Epic-2.

Fail: The save proceeds without confirmation, the hierarchy changes before the
user confirms, or the visible dialog summary omits Story-A, the descendant
count, or Epic-2.
```
