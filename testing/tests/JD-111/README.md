# JD-111 test automation

Reproduces the JD-111 expectation that the project's `index.html` page exposes
extended project information to a user.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/JD-111/test_jd_111.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- Optional override:
  - `JD111_INDEX_URL` — defaults to the repository `web/index.html` file URL

## Expected result

```text
Pass: The index page loads and visibly shows the extended project information
sections Browser Extensions, Key Features, AI Automation Workflow, and Tech
Stack, with four feature cards and four workflow steps.

Fail: The page loads without those visible sections, or the expected counts are
missing from the user-visible page.
```
