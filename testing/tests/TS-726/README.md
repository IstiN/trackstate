# TS-726

Verifies the deployed TrackState workspace switcher remains keyboard-accessible and
meets the ticket's WCAG-focused accessibility checks for focus order, descriptive
semantics labels, badge text contrast, interactive icon contrast, and the condensed
mobile trigger focus ring.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-726/test_ts_726.py
```

## Required environment / config

Requires `GH_TOKEN` or `GITHUB_TOKEN` for the live hosted app session. The defaults are:

- app URL: `https://istin.github.io/trackstate-setup/`
- repository: `IstiN/trackstate-setup`
- ref: `main`

## Expected passing output

```text
TS-726 passed
```
