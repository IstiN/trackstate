# TS-74

Validates the CLI quick-start fork connectivity path by reading the canonical
`README.md` from `IstiN/trackstate-setup` (or a `TS74_DOCUMENTATION_REPOSITORY`
override), resolving the authenticated user's `trackstate-setup` fork by
default, extracting an executable GitHub CLI command from the `CLI quick
start` section, and running that documented command against the fork. The test
only passes when the setup README documents a runnable quick-start command
whose JSON output matches the fork's live `DEMO/project.json`.

## Install dependencies

No Python packages are required beyond the standard library. Ensure these tools
are available before running the test:

1. `python3`
2. `gh`
3. An authenticated GitHub CLI session (`gh auth status`)
4. A fork of `IstiN/trackstate-setup` for the authenticated GitHub user, or a
   `TS74_SETUP_REPOSITORY` / `TRACKSTATE_SETUP_REPOSITORY` override that points
   to a fork of `IstiN/trackstate-setup`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-74 -p 'test_*.py'
```

## Environment variables

- `TS74_SETUP_REPOSITORY` or `TRACKSTATE_SETUP_REPOSITORY` (optional): setup
  repository to validate. When omitted, the test targets
  `<authenticated-login>/trackstate-setup`.
- `TS74_DOCUMENTATION_REPOSITORY` (optional): repository whose `README.md`
  provides the canonical CLI quick-start instructions. Defaults to
  `IstiN/trackstate-setup`.
- `TS74_UPSTREAM_SETUP_REPOSITORY` (optional): upstream template repository
  that the fork must point to. Defaults to `IstiN/trackstate-setup`.
- `TS74_FORK_REPOSITORY_NAME` (optional): repository name used when deriving the
  default fork from the authenticated login. Defaults to `trackstate-setup`.
- `TS74_PROJECT_PATH` (optional): project file path inside the setup repository.
  Defaults to `DEMO/project.json`.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
