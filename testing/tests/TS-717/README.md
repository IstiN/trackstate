# TS-717

Validates that choosing an already committed local TrackState repository from
the onboarding flow is inspected as ready-to-open, keeps the ready-state UI
visible, and opens the workspace without modifying the selected folder on disk.

The automation:
1. creates a temporary local Git repository fixture with the required
   TrackState scaffold on `main`
2. verifies the production `LocalGitWorkspaceOnboardingService` classifies that
   folder as `readyToOpen`
3. launches the onboarding screen, chooses `Open existing folder`, and records
   the exact folder path passed into `inspectFolder(...)`
4. verifies the Workspace details step shows the expected ready-state copy,
   prefilled workspace name/write branch values, enabled `Open workspace`
   action, and non-empty interactive semantics labels
5. opens the workspace and verifies the dashboard becomes visible while the
   repository HEAD, worktree status, and file manifest stay unchanged

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-717/test_ts_717.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the prepared committed local TrackState repository is inspected as
ready-to-open, the onboarding UI advances to Workspace details with Open
workspace enabled, semantics labels stay non-empty, and opening the workspace
does not change the selected folder on disk.

Fail: the selected folder is not the one inspected, the ready-state UI does not
render with the expected values, semantics labels are missing, or opening the
workspace mutates the repository or fails to reach the dashboard.
```
