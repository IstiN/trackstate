# TS-721

Validates that completing the first-run local onboarding flow saves the local
workspace profile and opens the Tracker UI immediately.

The automation:
1. launches the production first-run onboarding screen with no saved workspaces
2. selects a valid local Git repository through the injected directory picker
3. captures the local workspace details, submits `Open workspace`, and verifies
   the production `WorkspaceProfileService` records the local workspace input
4. verifies the saved local workspace becomes active and the Tracker dashboard
   opens immediately
5. verifies the visible local repository context shows the expected Local Git
   access state and seeded issue content

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-721/test_ts_721.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No external service credentials are required

## Expected result

```text
Pass: completing first-run local onboarding saves the workspace profile,
activates the selected local repository, closes onboarding, and shows the
Tracker dashboard with the Local Git repository context.

Fail: the local workspace profile is not created, the saved workspace does not
become active, routing does not leave onboarding, or the Tracker UI does not
show the selected local repository context.
```
