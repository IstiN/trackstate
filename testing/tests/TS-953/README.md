# TS-953

Verifies that a live pull-request accessibility run still reports a standard
network or Playwright timeout when the page load itself stalls, instead of
misclassifying that failure as a Flutter semantics initialization problem.

The automation:
1. creates a disposable branch and pull request against `IstiN/trackstate`,
2. changes only `testing/accessibility/` files to stall the initial navigation
   request before Flutter semantics initialization begins,
3. waits for the live `Flutter Required Checks` pull-request workflow and
   `Accessibility checks` status check to finish, and
4. inspects the contributor-visible GitHub Actions log for a generic timeout
   signal and the absence of Flutter-semantics failure wording.

## Prerequisites

- Python 3.12+
- `gh` CLI authenticated with push access to `IstiN/trackstate`
- Network access to GitHub Actions, pull requests, and workflow logs
- Defaults come from `testing/tests/TS-953/config.yaml`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-953/test_ts_953.py
```

## Disposable PR behavior

- The probe creates a temporary branch and pull request in the live repository.
- The disposable PR only adds the TS-953 network-timeout helper and patches the
  accessibility gate spec under `testing/accessibility/`.
- The probe closes the temporary pull request and deletes its branch during
  cleanup after collecting the workflow evidence.

## Expected failure evidence

- The accessibility workflow run completes with the `Accessibility checks`
  surface in `failure`.
- The GitHub Actions log includes a generic page-load/network timeout path such
  as `page.goto`, `page.waitForLoadState`, `networkidle`, or a standard
  Playwright timeout.
- The log should not claim that Flutter semantics nodes failed to render or that
  the failure was a `page.waitForFunction` semantics-initialization timeout.
