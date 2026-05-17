# TS-617

Verifies that the hosted **Project Settings → Repository access** `Connect token`
button behaves like a standard keyboard-activatable button after it receives
focus through tab navigation.

The automation:
1. opens the deployed hosted TrackState app in a Chromium Playwright session
   using the configured GitHub token
2. navigates to **Project Settings → Repository access**
3. confirms the visible **Fine-grained token**, **Remember on this browser**,
   and **Connect token** controls are present in the same repository-access
   section
4. tabs from the token field to the visible **Connect token** button and presses
   `Enter`
5. verifies the live page surfaces new visible connection feedback after keyboard
   activation
6. refreshes the page, repeats the keyboard navigation, and presses `Space`
7. verifies the live page again surfaces new visible connection feedback after
   keyboard activation
8. writes the required result artifacts to `outputs/`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-617/test_ts_617.py
```

## Required environment / config

Requires `GH_TOKEN` or `GITHUB_TOKEN` for the live hosted app session. The
defaults are:

- app URL: `https://istin.github.io/trackstate-setup/`
- repository: `IstiN/trackstate-setup`
- ref: `main`

## Expected passing output

```text
TS-617 passed
```
