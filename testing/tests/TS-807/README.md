# TS-807 test automation

Verifies that the deployed desktop workspace switcher stays open when the user
clicks a non-interactive or blank area inside the already-open panel.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-807/test_ts_807.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, opening the workspace switcher and clicking a non-interactive
area inside the open panel keeps the panel visible and functional.

Fail: the inside click dismisses the panel, changes it into an unexpected
container, or causes the visible workspace-switcher content to disappear.
```
