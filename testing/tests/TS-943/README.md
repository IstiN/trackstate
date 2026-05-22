# TS-943

Verifies that the live pull-request accessibility workflow fails when the
Flutter engine lifecycle logging wrapper is suppressed and the CI surface is
expected to reject missing engine-state tokens.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. changes only `testing/accessibility/` files to silence the engine-state log
   wrapper in `accessibility_gate.spec.js`,
3. waits for the live `Flutter Required Checks` workflow to finish, and
4. inspects the contributor-visible run summary and logs for a failing
   `log-validation` step with an explicit missing-token message.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-943/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-943/test_ts_943.py
```
