# TS-94

Validates the dirty-local-files create flow in the real Local Git runtime.

The automation:
1. creates a temporary local Git repository fixture
2. dirties `DEMO/DEMO-1/main.md` outside TrackState
3. launches the real `TrackStateApp` in Local Git mode
4. verifies the repository is loaded from **JQL Search**
5. scans the visible top-level sections for a production-visible `Create issue`
   entry point
6. if found, opens the create flow, enters issue details, submits the action,
   and verifies visible `commit` / `stash` / `clean` guidance
7. if not found, fails with a user-visible UI snapshot that documents the
   product gap

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-94/test_ts_94.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: a reachable create flow surfaces visible commit/stash/clean guidance when
the local repository is dirty.

Fail: Local Git issue creation is not production-visible yet, or the reachable
create flow does not expose the required input and submission controls.
```
