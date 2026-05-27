# TS-704

Validates that saving a hosted workspace immediately opens that workspace and
shows the in-context GitHub access prompt when write access is not connected.

The automation:
1. seeds an existing active hosted workspace for `owner/current@main`
2. opens the Add workspace flow and switches to `Hosted repository`
3. selects the visible `owner/next-repo` suggestion and submits `Open`
4. verifies the production `WorkspaceProfileService` persists
   `hosted:owner/next-repo@release` as the active workspace
5. verifies the app returns to the workspace dashboard and shows the inline
   disconnected GitHub access prompt for the new hosted workspace

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-704/test_ts_704.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: saving the hosted workspace closes onboarding, switches the active
workspace to owner/next-repo@release, returns to the dashboard, and shows the
inline Connect GitHub prompt for the new workspace context.

Fail: the selected hosted workspace is not persisted as active, routing does
not return to the dashboard, or the in-context GitHub access prompt is missing.
```
