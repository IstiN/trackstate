# TS-1324

Verifies that the live `IstiN/trackstate-setup` `actionlint` gate rejects a
workflow file that lacks a job-level `timeout-minutes` setting.

## Install dependencies

```bash
python3 -m pip install -r testing/requirements.txt
```

## Run this test

```bash
PYTHONPATH=. TS1324_RESULT_PATH=outputs/ts1324_observation.json \
python3 -m unittest discover -s testing/tests/TS-1324 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with push access to
  `IstiN/trackstate-setup`.
- Network access to GitHub REST APIs and GitHub Actions logs is required.
- Optional: set `TS1324_RESULT_PATH` to capture the live observation JSON.

## Expected passing output

```text
test_actionlint_rejects_workflows_missing_timeout_minutes ... ok
```
