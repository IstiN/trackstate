# TS-665

Validates the first-run workspace migration that converts a valid legacy hosted
repository context into one active workspace and migrates only that active
repository token into workspace scope.

The automation:
1. seeds legacy SharedPreferences entries for the active hosted repository token
   and an unrelated second legacy repository token
2. runs the production workspace migration flow for the active hosted context
3. verifies `WorkspaceProfileStore` persists exactly one active workspace and
   marks migration complete
4. verifies `WorkspaceCredentialStore` moves only the active repository token to
   the encoded workspace-scoped key while leaving the unrelated legacy token
   untouched
5. pumps the production app with the migrated state and confirms the hosted user
   still appears connected with visible profile identity

## Run this test

```bash
flutter test testing/tests/TS-665/test_ts_665.dart
```

## Required configuration

This test uses mocked SharedPreferences and the production demo hosted
repository, so no external credentials or live services are required.

## Expected result

The first migration seeds exactly one active hosted workspace for the current
repository context, stores the active token under the workspace-scoped auth key,
removes the old repository-scoped token for that workspace, leaves unrelated
legacy tokens unmigrated, and still restores the connected hosted identity that
the user sees in the app.
