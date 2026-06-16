# TS-681

Validates that TrackState can bootstrap from a legacy or partially populated
hosted workspace profile already stored in browser local storage.

The automation preloads one Hosted workspace entry that is missing the legacy
metadata object, opens the deployed app, and verifies the user-visible outcome:
1. startup reaches the interactive shell instead of the fatal data banner, and
2. **Project Settings** / **Saved workspaces** renders safe fallback values for
   the stored Hosted workspace row.

The test also records the repaired Flutter web storage payload as diagnostic
evidence, but pass/fail depends only on the ticket's required user-visible
behavior.

## Install dependencies

Install the browser automation dependency used by the live browser tests:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-681/test_ts_681.py
```

## Environment variables

- `GH_TOKEN` or `GITHUB_TOKEN`: required so the live app can authenticate
  against the hosted repository.

## Expected passing output

```text
TS-681 passed
```

## Expected behavior

When the deployed app starts with a preloaded hosted workspace profile missing
legacy metadata fields, it should still reach the interactive shell and the
Saved workspaces list should show fallback Hosted row text without broken
placeholder values.
