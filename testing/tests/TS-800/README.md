# TS-800

Validates that selecting an existing Git repository during first-launch
onboarding is recognized correctly, skips re-initialization, and allows the
user to continue with the ready-to-open flow.

The automation:
1. creates a temporary committed local TrackState repository fixture
2. verifies the production local onboarding service classifies that folder as
   `readyToOpen`
3. launches the onboarding screen, chooses `Open existing folder`, and selects
   the prepared repository through the directory picker
4. verifies the rendered ready-state copy, selected folder path, and enabled
   `Open workspace` action instead of a re-initialization CTA
5. opens the workspace and verifies the dashboard becomes visible without
   mutating the selected repository on disk

## Run this test

```bash
flutter test testing/tests/TS-800/test_ts_800.dart --reporter expanded
```
