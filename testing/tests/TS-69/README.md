# TS-69 test automation

## Run this test

```bash
TS69_RESULT_PATH=outputs/ts69_run.json \
python -m unittest discover -s testing/tests/TS-69 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated for a GitHub user that can dispatch
  workflows on the fork configured in `testing/tests/TS-69/config.yaml`.
- Network access to GitHub REST APIs and the deployed Pages URL is required.

## Expected passing output

```text
test_workflow_builds_pages_artifact_without_committing_web_assets ... ok
```

On success the test also writes the observed live workflow and Pages details to
`TS69_RESULT_PATH` when that environment variable is provided.
