# TS-122

Validates that Local Git mode exposes a production-visible `Create issue`
entry point from Dashboard, Board, JQL Search, and Hierarchy.

The automation:
1. creates a temporary local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. visits Dashboard, Board, JQL Search, and Hierarchy in order
4. verifies each section exposes a visible `Create issue` entry point
5. opens the create flow from each reachable section and checks the visible
   `Summary`, `Description`, `Save`, and `Cancel` controls
6. closes the create flow before moving to the next section
7. fails with section-specific UI snapshots when any entry point is missing or
   not user-reachable

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-122/test_ts_122.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: each specified Local Git section exposes a visible Create issue entry
point and that entry point opens a user-usable issue creation flow.

Fail: one or more sections do not expose the Create issue entry point, or the
visible entry point does not open a create flow with the expected user-facing
controls.
```
