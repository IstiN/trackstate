# TS-250

Validates that opening a pull request to `main` in `IstiN/trackstate-setup`
exposes a successful release dry-run check before merge.

The automation:

1. reads the live release workflow source from the default branch,
2. creates a disposable branch with a minor `README.md` change,
3. opens a disposable pull request to `main`,
4. observes the pull request checks on GitHub Actions, and
5. verifies a contributor-visible dry-run release step completed successfully.

## Run this test

```bash
TS250_RESULT_PATH=outputs/ts250_observation.json \
python3 -m unittest discover -s testing/tests/TS-250 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to push branches to
  `IstiN/trackstate-setup`.
- Network access to GitHub REST APIs is required.

## Expected passing output

```text
test_pull_request_to_main_exposes_successful_release_dry_run ... ok
```
