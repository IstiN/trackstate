# TS-70 test automation

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-70/ts70_fine_grained_pat_auth_playwright.py
```

## Required environment

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate against the hosted setup repository
- The script targets the deployed GitHub Pages app at `https://istin.github.io/trackstate-setup/`

## Expected passing output

```text
TS-70 passed
```
