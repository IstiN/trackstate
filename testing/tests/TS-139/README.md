# TS-139

Validates that Local Git mode keeps a production-visible `Create issue` entry
point reachable across the primary app sections even when the repository is
dirty.

The automation:
1. creates a temporary local Git repository fixture
2. dirties `DEMO/DEMO-1/main.md` outside TrackState and confirms the worktree is dirty
3. launches the real `TrackStateApp` in Local Git mode
4. opens Dashboard, Board, JQL Search, Hierarchy, and Settings
5. verifies each section renders a visible `Create issue` entry point
6. verifies the visible entry point can be activated and the create form shows
   `Summary`, `Description`, `Save`, and `Cancel`
7. submits the create flow from `JQL Search` and verifies visible `commit` /
   `stash` / `clean` recovery guidance

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-139/test_ts_139.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: every specified Local Git section keeps a visible, user-reachable Create
issue action while the repository is dirty, and submitting the create flow
surfaces commit/stash/clean recovery guidance.

Fail: one or more sections hide or disable the Create issue entry point in dirty
state, or the reachable create flow does not surface the required guidance.
```
