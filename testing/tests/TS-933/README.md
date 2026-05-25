# TS-933

Verifies that the live pull-request accessibility gate reports a descriptive
Flutter semantics initialization failure instead of exposing only a generic
Playwright `page.waitForFunction` timeout.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. changes only `testing/accessibility/` files to simulate missing
   `flt-semantics` exposure during initialization,
3. waits for the live `Flutter Required Checks` pull-request workflow and
   `Accessibility checks` status check to finish, and
4. inspects the contributor-visible GitHub Actions log for descriptive
   semantics-failure evidence.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-933/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-933/test_ts_933.py
```

## Disposable PR behavior

- The probe creates a temporary branch and pull request in the live repository.
- The disposable PR only adds the TS-933 simulation helper and patches the
  accessibility gate spec under `testing/accessibility/`.
- The probe closes the temporary pull request and deletes its branch during
  cleanup after collecting the workflow evidence.

## Expected failure evidence

- The accessibility workflow run completes with the `Accessibility checks`
  surface in `failure`.
- The GitHub Actions log includes a descriptive message that the Flutter engine
  failed to expose or render semantics nodes during initialization.
- The log should not stop at the generic Playwright
  `page.waitForFunction` timeout path.
