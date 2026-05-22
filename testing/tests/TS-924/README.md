# TS-924

## Objective

Verify that the live pull-request CI pipeline allows a disposable PR to proceed
when the rendered probe keeps WCAG AA-compliant contrast and uses a descriptive
semantics label.

## Automation approach

This test exercises the real PR path:

1. creates a disposable branch and PR against `main`;
2. adds a Flutter probe widget under `lib/` with `colorScheme.onSurface` text on
   `colorScheme.surface` and a descriptive semantics label;
3. waits for the live `Flutter Required Checks` PR workflow run on that
   disposable PR;
4. inspects the actual PR checks surface, workflow jobs/steps, and run logs for
   a successful accessibility result that does not block the PR.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-924/test_ts_924.py
```
