# TS-968

Verifies that the local accessibility workflow contract test returns a non-zero
exit code when an assertion fails.

The automation:
1. runs `node testing/accessibility/log_validation.node.test.js` against the
   current repository as a control check,
2. stages a disposable local copy of the workflow and removes the mandatory
   `log-validation` step,
3. reruns the same Node command against that disposable copy, and
4. confirms the terminal output shows the failing subtest and that the process
   exits with code `1`.

## Prerequisites

- Python 3.12+
- Node.js available on `PATH`
- Defaults come from `testing/tests/TS-968/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-968/test_ts_968.py
```
