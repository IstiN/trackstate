# TS-401

Validates the live hosted multi-view edit flow against the deployed tracker at
`https://istin.github.io/trackstate-setup/`.

The automation:
1. prefers the live `DEMO-5` issue and falls back to another non-epic live issue
   that is not already `Done` / `Highest`
2. opens the production **Edit issue** surface for that issue from the live
   **Board** view
3. uses the live workflow path to reach a real **Done** transition when the
   current issue is still one or more workflow steps away from **Done**
4. attempts the real user workflow to change **Priority** to `Highest` and
   **Status** to `Done`
5. saves the edit when the hosted UI exposes the required controls
6. verifies the refreshed projections from **Board**, **Hierarchy**, and
   **JQL Search**
7. fails with product-visible evidence when the hosted app does not expose the
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
Pass: the selected live issue can be edited from the hosted app, saved, and the
updated Priority/Status state propagates across Board, Hierarchy, and JQL Search
without a manual reload.

Fail: the hosted app does not expose the required transition or edit controls,
the save path does not complete, or one of the dependent views does not refresh
to the edited state.
```
