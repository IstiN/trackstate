# TS-961

## Objective

Verify that the live GitHub Actions accessibility workflow executes
`log-validation` after a successful `Run axe-core accessibility checks` step
and that the validator reports its success marker.

## Automation approach

1. Create a disposable pull request that contains valid accessibility-only
   changes.
2. Wait for the pull-request workflow run on `main` to start and capture the
   contributor-visible accessibility job details.
3. Inspect the workflow sequence to confirm `log-validation` executes
   immediately after the successful axe-core scan.
4. Read the hosted run log and verify the validator success marker proving the
   mandatory logs were found.

## Prerequisites

- `gh` must be installed and authenticated with permission to push branches and
  open pull requests in `IstiN/trackstate`.
- Network access to GitHub pull requests, Actions metadata, and workflow logs
  is required.
- Python dependencies from the repository environment must be available, and
  `PYTHONPATH=.` must point at the repository root when running the test.

## Run command

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-961/test_ts_961.py
```
