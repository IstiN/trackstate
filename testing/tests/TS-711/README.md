# TS-711

Validates that switching workspaces disposes the current background sync
coordinator and starts a new one for the selected workspace immediately.

The automation:
1. seeds two valid local workspaces and launches the production app with
   Workspace-A active
2. opens the workspace switcher, selects Workspace-B, and waits for the visible
   active workspace summary to change
3. records the production sync repository check log for both workspaces to prove
   Workspace-B starts an immediate first sync without waiting 60 seconds
4. advances fake time past 60 seconds and verifies Workspace-A stays idle after
   disposal so its old cadence timer never fires again

## Run this test

```bash
flutter test testing/tests/TS-711/test_ts_711.dart --reporter expanded
```
