# TS-709

Validates that the live `Apple Release Builds` workflow remains isolated from
normal `main` pushes while still showing runtime evidence of semantic tag
release execution.

The automation covers the production-visible GitHub Actions behavior by:
1. loading the live workflow definitions for `Apple Release Builds` and
   `Flutter CI`
2. confirming the Apple workflow is tag-scoped and the general CI workflow
   still listens to `main`
3. checking recent Apple workflow run logs for semantic version tag evidence
4. confirming the current `main` head continues through general CI without
   appearing in Apple workflow push runs
5. opening the live GitHub workflow pages for browser-style verification

## Install dependencies

```bash
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-709/test_ts_709.py
```

## Required configuration

- GitHub CLI authenticated with repository and workflow scopes
- Playwright Chromium runtime available for GitHub file-page verification

## Assertions

- `Apple Release Builds` exposes `push.tags: [v*]` and does not listen to
  normal `main` pushes
- `Flutter CI` still listens to pushes on `main`
- recent Apple workflow runs include semantic-tag evidence in their live logs
- the current `main` head appears on recent general CI push runs and not on
  recent Apple workflow push runs
