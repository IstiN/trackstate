# TS-140

Validates that Local Git issue creation succeeds after the user resolves a dirty
repository state and retries from the same create flow.

The automation:
1. creates a temporary local Git repository fixture
2. dirties `DEMO/DEMO-1/main.md` outside TrackState
3. launches the real `TrackStateApp` in Local Git mode
4. opens the production-visible `Create issue` flow and submits it while dirty
5. verifies the visible `commit` / `stash` / `clean` recovery guidance
6. stashes the filesystem changes outside the app, then retries the same create
   action without reopening the dialog
7. verifies the dialog closes, the created issue is visible in search, and the
   new issue is committed to Git history

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-140/test_ts_140.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected result

```text
Pass: the first submit attempt is blocked with visible dirty-repository
guidance, then the second submit attempt succeeds after the repository is
cleaned via git stash.
```
