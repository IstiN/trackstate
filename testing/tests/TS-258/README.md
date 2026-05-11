# TS-258

Validates that the live `actionlint` gate in `IstiN/trackstate-setup` covers
newly added workflow files anywhere under `.github/workflows/`.

The automation creates a disposable branch, adds a brand-new invalid
`.github/workflows/new-utility.yml`, pushes the branch, and verifies that the
visible `actionlint` run fails and mentions the new file in its log output.

## Install dependencies

```bash
python3 -m pip install -r testing/requirements.txt
```
## Run this test

```bash
PYTHONPATH=. TS258_RESULT_PATH=outputs/ts258_observation.json \
python3 -m unittest discover -s testing/tests/TS-258 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to push branches to
  `IstiN/trackstate-setup`.
- Network access to GitHub REST APIs and GitHub Actions logs is required.
- Optional: set `TS258_RESULT_PATH` to capture the live observation JSON.

## Expected passing output

```text
test_extract_actionlint_log_excerpt_prefers_new_workflow_error_region ... ok
test_new_workflow_file_is_included_in_actionlint_coverage ... ok
```
