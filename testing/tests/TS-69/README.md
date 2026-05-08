# TS-69 test automation

## Run this test

```bash
TS69_RESULT_PATH=outputs/ts69_run.json \
python -m unittest discover -s testing/tests/TS-69 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated for a GitHub user that can dispatch
  workflows on their fork of the upstream repository configured in
  `testing/tests/TS-69/config.yaml`.
- Network access to GitHub REST APIs and the deployed Pages URL is required.

The test derives the fork repository from the authenticated `gh` login instead
of pinning a specific fork owner in source control.

## Expected passing output

```text
test_workflow_builds_pages_artifact_without_committing_web_assets ... ok
```

On success the test also writes the observed live workflow and Pages details to
`TS69_RESULT_PATH` when that environment variable is provided.

The live probe follows the newest workflow-dispatch run created after the test's
dispatch request so shared-environment cancellations do not produce false
failures.
