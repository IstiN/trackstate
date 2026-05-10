# TS-236

Validates that the executable `gh api` command documented in
`trackstate-setup/README.md` surfaces a user-visible authentication error when
the GitHub token is invalid.

The automation:
1. checks that `trackstate-setup/README.md` still contains the `CLI quick start`
   command required by the ticket
2. confirms the local GitHub CLI session can resolve the authenticated viewer
   login before credentials are intentionally invalidated
3. expands the documented command to the live setup repository for that login
4. reruns the exact README command with invalid `GH_TOKEN` / `GITHUB_TOKEN`
5. verifies the terminal output reports an authentication failure such as
   `Bad credentials` or HTTP 401 instead of a parsing/tooling error

## Install dependencies

No extra Python packages are required beyond the standard library. Ensure these
tools are available before running the test:

1. `python3`
2. `gh`
3. An authenticated GitHub CLI session that can resolve `gh api user --jq .login`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-236 -p 'test_*.py'
```

## Environment variables

- `TS236_INVALID_GITHUB_TOKEN` (optional): invalid token value injected into
  `GH_TOKEN` and `GITHUB_TOKEN` during the negative-path execution
- `TS74_SETUP_REPOSITORY` or `TRACKSTATE_SETUP_REPOSITORY` (optional): explicit
  setup repository override used by the shared CLI validation config
- `TS74_FORK_REPOSITORY_NAME` (optional): repository name paired with the
  authenticated login when no repository override is supplied
- `TS74_PROJECT_PATH` (optional): project file path used when expanding the
  README command; defaults to `DEMO/project.json`

## Expected result

```text
Pass: the copied README command fails with a visible authentication error after
the token is intentionally invalidated.

Fail: the README command disappears, the CLI prerequisites cannot resolve the
authenticated viewer login, or the terminal output shows a command-shape/tooling
failure instead of an authentication error.
```
