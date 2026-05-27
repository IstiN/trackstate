# TS-952

Verifies that the live pull-request accessibility gate fails with a descriptive
missing-`flt-semantics-placeholder` pre-flight error instead of progressing into
the generic timeout-prone polling path.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. changes only `testing/accessibility/` files to hide
   `flt-semantics-placeholder` from the live gate,
3. waits for the live `Flutter Required Checks` pull-request workflow and
   `Accessibility checks` status check to finish, and
4. inspects the contributor-visible GitHub Actions log for a descriptive
   missing-placeholder failure message and absence of polling-timeout evidence.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-952/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-952/test_ts_952.py
```

## Disposable PR behavior

- The probe creates a temporary branch and pull request in the live repository.
- The disposable PR only adds the TS-952 simulation helper and patches the
  accessibility gate spec under `testing/accessibility/`.
- The probe closes the temporary pull request and deletes its branch during
  cleanup after collecting the workflow evidence.

## Expected failure evidence

- The accessibility workflow run completes with the `Accessibility checks`
  surface in `failure`.
- The GitHub Actions log identifies the missing
  `flt-semantics-placeholder` directly during pre-flight validation.
- The log should not degrade into a generic Playwright timeout or continue into
  the later semantics polling/runtime-ready path.
