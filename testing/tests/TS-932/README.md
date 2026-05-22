# TS-932

## Objective

Verify that the live pull-request accessibility gate logs successful
`flt-semantics-placeholder` verification before the hosted WCAG accessibility
scan proceeds.

## Automation approach

This test exercises the real PR path:

1. creates a disposable WCAG-compliant pull request against `main`;
2. waits for the live `Flutter Required Checks` pull-request workflow run to
   complete on that disposable branch;
3. reads the contributor-visible `Accessibility checks` stage log from GitHub
   Actions; and
4. fails unless the log shows `flt-semantics-placeholder` verification before
   the runtime accessibility surface is reported ready and the stage completes.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-932/test_ts_932.py
```

## Disposable PR behavior

- The probe creates a temporary branch and pull request in the live repository.
- The disposable PR renders the same WCAG-compliant Flutter probe pattern used
  for the passing accessibility-gate scenario.
- The probe closes the temporary pull request and deletes its branch during
  cleanup after collecting the workflow evidence.
