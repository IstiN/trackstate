# TS-950

Verifies that the live pull-request CI contract rejects workflow changes that
remove the mandatory contributor-visible `log-validation` step from the
accessibility job.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. removes only the `log-validation` step from `.github/workflows/unit-tests.yml`,
3. waits for the live `Flutter Required Checks` pull-request workflow, and
4. checks that GitHub reports a failing schema/contract validation with an
   explicit missing-step message and a merge-blocked PR surface.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-950/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-950/test_ts_950.py
```
