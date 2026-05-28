# TS-969

Verifies that the live CI wrapper around `npm run test:a11y` captures a failing
contract-validation script and propagates exit code `1` to the GitHub Actions
step.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. adds a ticket-specific failing node test under `testing/accessibility/`,
3. patches `package.json` so `npm run test:a11y` executes that failing test,
4. waits for the live `Flutter Required Checks` workflow to complete, and
5. checks that the contributor-visible wrapper step logs the failure message and
   exits with code `1`.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-969/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-969/test_ts_969.py
```
