# TS-237

Validates the README `CLI quick start` command behavior when the target
`DEMO/project.json` file is missing from the fork under test. The test reads the
deployed `IstiN/trackstate-setup` quick-start documentation, extracts the
documented `gh api` validation command, executes that exact command against the
fork under test, and expects the terminal-visible result to be a 404 error
instead of JSON content.

## Install dependencies

No Python packages are required beyond the standard library. Ensure these tools
are available before running the test:

1. `python3`
2. `gh`
3. An authenticated GitHub CLI session (`gh auth status`)
4. A fork of `IstiN/trackstate-setup` for the authenticated GitHub user, or a
   `TS74_SETUP_REPOSITORY` / `TRACKSTATE_SETUP_REPOSITORY` override that points
   to a fork of `IstiN/trackstate-setup` where `DEMO/project.json` is missing
   or renamed

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-237 -p 'test_*.py'
```

## Environment variables

- `TS74_SETUP_REPOSITORY` or `TRACKSTATE_SETUP_REPOSITORY` (optional): setup
  repository to validate. When omitted, the test targets
  `<authenticated-login>/trackstate-setup`.
- `TS74_UPSTREAM_SETUP_REPOSITORY` (optional): upstream template repository
  that the fork must point to. Defaults to `IstiN/trackstate-setup`.
- `TS74_FORK_REPOSITORY_NAME` (optional): repository name used when deriving the
  default fork from the authenticated login. Defaults to `trackstate-setup`.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
