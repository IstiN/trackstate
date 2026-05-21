# TS-887

Reproduces the deployed hosted **Edit issue** Summary validation accessibility
scenario from the user's perspective.

The automation:
1. opens the live hosted TrackState app
2. connects the session with the configured GitHub token
3. opens the live **Edit issue** surface for `DEMO-2`
4. attempts to clear the visible `Summary` field
5. stops with a failed result if the production UI does not allow the user to
   perform that first required action

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-887/test_ts_887.py
```

## Expected result

```text
Pass: the Summary field is editable, the user can clear it, and the remaining
validation checks can run.

Fail: the deployed Edit issue surface renders Summary as non-editable/disabled,
so the user cannot trigger the required validation feedback scenario.
```
