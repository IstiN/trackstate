# TS-401

Validates the live hosted multi-view edit flow for `DEMO-3` against the deployed
tracker at `https://istin.github.io/trackstate-setup/`.

The automation:
1. opens the production **Edit issue** surface for `DEMO-3`
2. attempts the real user workflow to change **Priority** to `Highest` and
   **Status** to `Done`
3. saves the edit when the hosted UI exposes the required controls
4. verifies the refreshed projections from **Board**, **Hierarchy**, and
   **JQL Search**
5. fails with product-visible evidence when the hosted app does not expose the
   required mutation capability

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-401/test_ts_401.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with write access to `IstiN/trackstate-setup`
- network access to the hosted app and GitHub API

## Expected result

```text
Pass: DEMO-3 can be edited from the live hosted app, saved, and the updated
Priority/Status state propagates across Board, Hierarchy, and JQL Search
without a manual reload.

Fail: the hosted app does not expose the required transition or edit controls,
the save path does not complete, or one of the dependent views does not refresh
to the edited state.
```
