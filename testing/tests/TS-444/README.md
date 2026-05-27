# TS-444

Validates the live hosted recovery entry point for a recoverable GitHub rate
limit during deferred bootstrap against `https://istin.github.io/trackstate-setup/`.

The automation:
1. opens the deployed hosted tracker
2. blocks `DEMO/.trackstate/index/tombstones.json` with a synthetic GitHub
   rate-limit 403 during deferred bootstrap
3. verifies the app shell remains visible instead of collapsing into a dead end
4. verifies the user lands in **Settings** and the Settings admin content is
   active

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-444/test_ts_444.py
```

## Required environment and config

- network access to the hosted app and the public GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: a recoverable deferred-bootstrap rate limit still renders the tracker app
shell, exposes the recovery affordances, and selects Settings automatically.

Fail: the rate-limited deferred bootstrap does not occur, the hosted shell does
not remain visible, or the visible selected section is not Settings.
```

