# TS-970

Verifies that the live pull-request accessibility contract validation drives the
contributor-visible `Flutter Required Checks` aggregate status and keeps the
pull request blocked from merge.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. removes only the mandatory `log-validation` step from
   `.github/workflows/unit-tests.yml` to violate the accessibility contract,
3. waits for the live `Flutter Required Checks` pull-request workflow, and
4. confirms the aggregate PR status fails because of the accessibility contract
   violation and the PR remains merge-blocked.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-970/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-970/test_ts_970.py
```
