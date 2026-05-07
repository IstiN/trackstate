# TS-74

Validates the CLI quick-start fork connectivity path by executing a GitHub CLI
command that reads the setup repository project definition and comparing the
JSON output to the checked-in `trackstate-setup/DEMO/project.json` fixture.

## Install dependencies

No Python packages are required beyond the standard library. Ensure these tools
are available before running the test:

1. `python3`
2. `gh`
3. An authenticated GitHub CLI session (`gh auth status`)

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-74 -p 'test_*.py'
```

## Environment variables

- `TS74_SETUP_REPOSITORY` or `TRACKSTATE_SETUP_REPOSITORY` (optional): setup
  repository to validate. Defaults to `IstiN/trackstate-setup`.
- `TS74_PROJECT_PATH` (optional): project file path inside the setup repository.
  Defaults to `DEMO/project.json`.
- `TS74_EXPECTED_PROJECT_FILE` (optional): repository-relative path to the
  expected JSON fixture. Defaults to `trackstate-setup/DEMO/project.json`.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
