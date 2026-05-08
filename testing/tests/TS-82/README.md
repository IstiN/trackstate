# TS-82

Validates that the upstream template repository keeps
`.github/workflows/install-update-trackstate.yml` on its default branch so future
forks inherit the workflow registration fix from TS-77.

The test performs two layers of verification against the live implementation:

1. GitHub CLI reads the upstream repository metadata, default branch tree,
   `.github/workflows` directory listing, and the workflow entry metadata.
2. Playwright opens the public GitHub directory page for that default branch and
   verifies the workflow filename is visibly listed for a human user.

## Run

```bash
python3 -m unittest discover -s testing/tests/TS-82 -p 'test_*.py' -v
```

## Environment variables

- `TS82_TEMPLATE_REPOSITORY` or `TRACKSTATE_TEMPLATE_REPOSITORY` (optional):
  template repository to validate. Defaults to `IstiN/trackstate-setup`.
- `TS82_WORKFLOW_PATH` (optional): workflow path to verify. Defaults to
  `.github/workflows/install-update-trackstate.yml`.
- `TS82_EXPECTED_DEFAULT_BRANCH` (optional): explicit default branch name to
  require. Leave unset to accept whatever branch GitHub reports as the default.
