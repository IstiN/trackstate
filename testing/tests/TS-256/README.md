# TS-256

Validates that a syntactically valid GitHub Actions workflow change passes the
live `actionlint` gate in `IstiN/trackstate-setup`.

The automation creates a disposable branch, adds a harmless comment to
`.github/workflows/release-on-main.yml`, pushes the branch, and verifies that
GitHub Actions exposes a successful `actionlint` run plus a visible successful
`actionlint` job or step.

## Run this test

```bash
TS256_RESULT_PATH=outputs/ts256_observation.json \
python3 -m unittest discover -s testing/tests/TS-256 -p 'test_*.py' -v
```

## Required configuration

- GitHub CLI authenticated (`gh auth status`) with push and branch-delete
  permissions for `IstiN/trackstate-setup`
- `GH_TOKEN`/`GITHUB_TOKEN` available to `gh api`
- network access to `api.github.com` and `github.com`
