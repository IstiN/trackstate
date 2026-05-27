# TS-251

Validates that pushing an invalid release workflow to `IstiN/trackstate-setup`
is blocked by a live `actionlint` pipeline.

The automation creates a disposable branch, corrupts
`.github/workflows/release-on-main.yml` with invalid YAML, pushes the branch,
and then checks whether GitHub Actions exposes a failed `actionlint` run with a
visible failing job/step.

## Run this test

```bash
TS251_RESULT_PATH=outputs/ts251_observation.json \
python3 -m unittest discover -s testing/tests/TS-251 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to push branches to
  `IstiN/trackstate-setup`.
- Network access to GitHub REST APIs is required.

## Expected passing output

```text
test_push_invalid_release_workflow_is_blocked_by_actionlint ... ok
```
