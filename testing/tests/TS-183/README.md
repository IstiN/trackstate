# TS-183

Validates that Local Git mode can create and persist a new issue from the
Board view by using the production-visible top-bar `Create issue` action.

The automation:
1. creates a temporary local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens the `Board` section and verifies the top bar shows `Create issue`
4. opens the create flow, fills `Summary` and `Description`, and saves
5. searches for the new issue in `JQL Search` and verifies the result details
6. confirms Local Git persistence through the create commit, changed file, and
   clean worktree state

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-183/test_ts_183.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Board top bar exposes a visible Create issue action, saving a valid
issue succeeds, the issue is searchable in JQL Search, and Local Git persists
the new issue as a clean single-file commit.

Fail: the Board top-bar Create issue action is missing or unusable, the create
flow cannot be saved successfully, the new issue is not searchable afterward,
or the Local Git persistence checks do not match the expected create commit.
```
