# TS-934

## Objective

Verify that the live pull-request accessibility workflow logs Flutter engine
startup state transitions and semantics-tree discovery status in the hosted
`Accessibility checks` run output.

## Automation approach

1. Create a disposable WCAG-compliant PR against `main`.
2. Wait for the real `Flutter Required Checks` pull-request workflow run to
   complete on that disposable branch.
3. Inspect the contributor-visible PR checks surface plus the hosted
   `Accessibility checks` log.
4. Fail if the log does not contain Flutter engine initialization entries and a
   semantics discovery status line, because that remains a product-visible gap.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-934/test_ts_934.py
```

## Required environment and config

- `gh` authenticated with push access to `IstiN/trackstate`
- network access to GitHub pull requests, checks, and Actions logs
- runtime settings from `testing/tests/TS-934/config.yaml`
