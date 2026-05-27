# TS-83 test automation

This test verifies that the latest stable source snapshot of
`IstiN/trackstate-setup` exposes
`.github/workflows/install-update-trackstate.yml`.

The validator first confirms the workflow exists on the default branch as a live
control check, then compares the newest release publication time with the newest
tag commit time so the assertion targets the actual latest stable snapshot.

## Run this test

```bash
TS83_RESULT_PATH=outputs/ts83_observation.json \
python -m unittest discover -s testing/tests/TS-83 -p 'test_*.py' -v
```

## Optional environment variables

- `TRACKSTATE_RELEASE_SOURCE_REPOSITORY` (default: `IstiN/trackstate-setup`)
- `TRACKSTATE_RELEASE_SOURCE_BRANCH` (default: `main`)
- `TRACKSTATE_RELEASE_SOURCE_WORKFLOW_PATH`
  (default: `.github/workflows/install-update-trackstate.yml`)

The default runtime inputs are also recorded in `config.yaml`.
