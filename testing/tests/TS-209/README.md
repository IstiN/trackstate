# TS-209

Validates that cancelling Local Git issue creation closes the create form and
does not persist any draft data to the repository filesystem.

The automation:
1. creates a clean Local Git repository fixture whose project config declares the
   `Solution`, `Acceptance Criteria`, and `Diagrams` fields
2. launches the real `TrackStateApp` in Local Git mode
3. opens the production-visible `Create issue` flow and verifies those fields are
   visible to the user
4. enters summary, description, and custom-field values, then presses `Cancel`
5. verifies the create form closes without a visible save failure
6. verifies the cancelled draft issue is not visible from the user-facing search flow
7. inspects the Local Git repository state and requires no new issue file,
   filesystem change, git worktree change, or commit

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-209/test_ts_209.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form exposes Solution, Acceptance Criteria,
and Diagrams, accepts entered values, closes immediately on Cancel, and leaves
the Local Git repository unchanged.

Fail: any required create-form field is not visible, the dialog does not close,
the cancelled draft becomes visible in the UI, or the Local Git filesystem/git
state changes after cancellation.
```
