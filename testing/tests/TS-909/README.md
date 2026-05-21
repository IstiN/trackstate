# TS-909

Validates that the live `IstiN/trackstate` GitHub repository exposes a pull
request template whose visible checklist includes the exact manual accessibility
item:

`Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.`

The automation checks the live implementation in two ways:

1. GitHub CLI reads repository metadata, the GitHub community profile, the
   default-branch tree, and conventional PR template file paths.
2. Playwright opens the live GitHub file page for the resolved PR template path
   (or the conventional `.github/PULL_REQUEST_TEMPLATE.md` path when no template
   exists) and verifies what a human would visibly observe in the browser.

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py
```
