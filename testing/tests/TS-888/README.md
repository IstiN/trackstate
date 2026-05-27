# TS-888

Verifies that the hosted app shell exposes a discoverable **Settings** primary
navigation action and that the **Project Settings** admin tabs remain visibly
interactive after the user opens that surface.

The automation:
1. opens the deployed TrackState app in a Chromium Playwright session using the
   configured GitHub token
2. waits for the default hosted shell to expose the primary navigation labels
3. confirms **Settings** is visibly present before interaction
4. opens **Project Settings**
5. verifies the **Statuses**, **Workflows**, and **Issue Types** tabs render and
   can each become the selected tab with their expected visible content
6. writes the required result artifacts to `outputs/`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-888/test_ts_888.py
```

## Required environment / config

Requires `GH_TOKEN` or `GITHUB_TOKEN` for the live hosted app session. The
defaults are:

- app URL: `https://istin.github.io/trackstate-setup/`
- repository: `IstiN/trackstate-setup`
- ref: `main`

## Expected passing output

```text
TS-888 passed
```
