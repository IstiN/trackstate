# TS-400

Validates that a sub-task keeps **Epic** derived from its **Parent** during the
production edit flow and does not allow direct Epic editing.

The automation:
1. launches the real local-repository-backed app with `SUBTASK-1` under
   `STORY-A` in `EPIC-1`
2. opens the production **Edit** dialog for `SUBTASK-1`
3. verifies **Parent** is editable, **Epic** is read-only, and the initial
   derived Epic is `EPIC-1 · Epic-1 platform rollout`
4. changes **Parent** to `STORY-B · Story-B parent in Epic-2` and verifies the
   visible derived Epic updates to `EPIC-2 · Epic-2 mobile refresh`
5. confirms **Epic** remains non-editable after the parent change and ends once
   the edit-surface assertions required by TS-400 are satisfied

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-400/test_ts_400.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own local Git repository fixture

## Expected result

```text
Pass: Editing SUBTASK-1 keeps Epic non-editable and re-derives the visible Epic
value from `EPIC-1` to `EPIC-2` when Parent changes from `STORY-A` to
`STORY-B`.

Fail: Epic is editable for the sub-task, the derived Epic does not update when
Parent changes, or the visible edit surface does not show the expected derived
Epic state.
```
