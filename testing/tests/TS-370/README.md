# TS-370

Verifies the global hosted repository-access banner stays visible across the
main issue flows, reflects the current access mode, and routes users to the
canonical recovery surface.

The automation:
1. opens the deployed web app in an unauthenticated hosted session
2. verifies the disconnected repository-access banner across Dashboard, Board,
   JQL Search, Hierarchy, and a real issue detail view
3. clicks the visible banner CTA and completes the PAT dialog through the live
   UI
4. patches the live repository permission response to read-only so the deployed
   app must render the read-only repository-access mode
5. verifies the read-only banner remains visible across the same issue flows
6. clicks the read-only recovery CTA and verifies the canonical settings/auth
   recovery surface opens

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-370/test_ts_370.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Python 3 available on `PATH`
- Playwright Chromium installed locally
- The test runs against the deployed app URL from
  `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the deployed banner stays visible across the covered flows, updates from
the disconnected mode to the read-only mode after the live PAT flow, and the
recovery CTA opens Project Settings / Repository access (or the auth dialog).

Fail: the banner disappears on a covered flow, the PAT dialog cannot be used,
the read-only mode never becomes visible, or the recovery CTA does not route to
the canonical recovery surface.
```
