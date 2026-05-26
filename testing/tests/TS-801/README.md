# TS-801

Validates that the first-launch onboarding flow inspects a real local folder
containing only hidden non-Git files and blocks initialization when the
selected folder is not supported.

The automation:
1. creates a temporary directory fixture containing only hidden files
2. launches the production onboarding screen and chooses `Initialize folder`
3. records the folder path passed into the real `inspectFolder(...)` call
4. verifies the rendered status, guidance copy, selected folder path, and
   visible Initialize action state after inspection
5. fails as a product bug if the production flow still treats the hidden-files
   folder as initializable instead of blocked

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-801/test_ts_801.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the real onboarding inspectFolder call runs for the selected hidden-files
folder, the UI shows blocked-state guidance that tells the user to choose an
existing Git repository or an empty folder, and the visible Initialize action
stays disabled.

Fail: the production inspection is bypassed, the selected folder is not the one
inspected, the blocked-state guidance is missing, or the visible Initialize
action remains enabled for the unsupported folder.
```
