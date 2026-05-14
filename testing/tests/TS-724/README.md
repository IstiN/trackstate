# TS-724

Validates that selecting a saved local workspace whose folder was deleted fails
validation before the active local workspace runtime is torn down.

The automation:
1. seeds a valid active local Workspace-A and a saved Workspace-B whose local
   folder is deleted from disk
2. launches the app through the TS-724 fixture/screen abstraction and waits for
   Workspace-A to finish rendering
3. attempts to switch to Workspace-B and verifies the production error message
   explains that the selected folder does not exist
4. proves Workspace-A was not reopened after the failed switch by asserting the
   post-attempt local-open sequence never returns to Workspace-A
5. verifies Workspace-A stays active while Workspace-B is marked unavailable

## Run this test

```bash
flutter test testing/tests/TS-724/test_ts_724.dart --reporter expanded
```
