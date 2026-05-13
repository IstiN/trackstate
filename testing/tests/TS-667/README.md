# TS-667

Validates that deleting the active saved workspace from *Project Settings*
requires an explicit confirmation, removes the deleted workspace's scoped
credentials, and visibly falls back to the remaining saved workspace.

The automation:
1. launches the live Flutter *Settings* surface with two saved hosted
   workspaces where W2 is active
2. verifies the destructive confirmation dialog copy for deleting W2
3. confirms the delete action and verifies the visible saved-workspaces section
   now shows only W1 as the active workspace
4. exercises the production `WorkspaceProfileService` deletion flow against
   shared preferences storage
5. verifies the deleted workspace token is removed and W1 is persisted as the
   active fallback workspace

## Run this test

```bash
flutter test testing/tests/TS-667/test_ts_667.dart --reporter expanded
```

## Required configuration

This test uses Flutter widget and shared-preferences fixtures only. No external
service credentials are required.

## Expected result

Deleting the active saved workspace should require confirmation, remove the
workspace-scoped credentials for W2, and leave W1 as the only remaining active
saved workspace.
