# TS-935

## Objective

Verify that the live pull-request CI pipeline executes the downstream deployment
stage when the accessibility audit passes on a disposable PR with WCAG-compliant
UI content.

## Automation approach

1. creates a disposable pull request with the compliant rendered accessibility
   probe used by the live PR accessibility gate;
2. waits for the live `Flutter Required Checks` pull-request workflow run;
3. opens the real GitHub Actions run page for human-style verification; and
4. verifies that the accessibility audit passes and the downstream
   deploy/publish stage executes successfully.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-935/test_ts_935.py
```
