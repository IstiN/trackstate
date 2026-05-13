# TS-405

Validates status catalog administration rejects duplicate status identifiers and
missing required attributes before any project-settings write reaches the Local
Git repository.

The automation:
1. launches the shipped Settings surface against a mutation-capable Local Git
   fixture seeded with an existing `in-progress` status
2. opens **Settings** > **Statuses** and confirms the seeded status is visible
3. creates a new draft status with duplicate ID `in-progress` and name `Doing`
4. saves the draft, then clicks **Save settings** and checks for the expected
   duplicate-ID validation message without any repository write
5. attempts to save another new status with a blank name and verifies the
   missing-name validation message without any repository write

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-405/test_ts_405.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture

## Expected result

```text
Current expected outcome: FAIL

The duplicate-ID save attempt should render:
Save failed: Status ID "in-progress" is defined more than once.

The missing-name save attempt should render:
Save failed: Statuses must include both an ID and a name.

The repository HEAD, worktree cleanliness, and DEMO/config/statuses.json must
remain unchanged for both blocked save attempts.
```
