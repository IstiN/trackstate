# TS-799

Validates that the first-launch onboarding flow treats a completely empty local
folder as a valid initialization target and lets the user continue.

The automation:
1. creates a temporary empty directory fixture with no files or hidden metadata
2. launches the production onboarding screen and chooses `Initialize folder`
3. records the real `inspectFolder(...)` call for the selected directory
4. verifies the rendered status, guidance copy, selected folder path, and the
   visible Initialize action state
5. clicks `Initialize TrackState here` and treats the scenario as successful
   only if the real initialization creates Git + TrackState scaffold data and
   opens the initialized workspace

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain
and the `git` executable already used by the production local onboarding flow.

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-799/test_ts_799.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- `git` available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the real onboarding inspectFolder call classifies the selected empty
folder as ready to initialize, the UI shows the initialization-required state
with the empty-folder guidance copy, the visible Initialize action is enabled,
and clicking it initializes the folder and opens the workspace.
```
