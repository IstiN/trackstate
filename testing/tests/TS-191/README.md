# TS-191

Validates that Local Git issue creation still enforces the required `Summary`
field even when the visible `Create issue` form contains valid custom-field
input.

The automation:
1. reuses the TS-141 Local Git custom-fields fixture so the production-visible
   create form exposes `Summary`, `Description`, `Solution`, and
   `Acceptance Criteria`
2. launches the real `TrackStateApp` in Local Git mode
3. opens `JQL Search`, then opens the visible `Create issue` flow
4. leaves `Summary` blank, enters valid values for `Description`, `Solution`,
   and `Acceptance Criteria`, then clicks `Save`
5. verifies the visible validation banner reports that `Summary` is required
6. verifies the create form stays open with the entered values still visible
7. verifies no new Local Git commit, worktree change, or `DEMO/DEMO-2/main.md`
   file is created

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-141/test_ts_141.dart testing/tests/TS-191/test_ts_191.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The TS-141 Local Git fixture provides the configured `Solution` and
  `Acceptance Criteria` custom fields required by this scenario

## Expected result

```text
Pass: saving with a blank Summary shows the visible "Issue summary is required"
validation error, the create form stays open with Description, Solution, and
Acceptance Criteria preserved, and Local Git remains unchanged.

Fail: the visible custom fields do not render, save succeeds, the validation
message is missing, the form closes or loses entered values, or any Local Git
file/commit is created.
```
