# TS-503 test automation

Verifies that a hosted `github-releases` attachment upload fails fast when the
expected release tag already exists with a mismatched issue identity title.

The automation:
1. seeds the live `DEMO` hosted project so `TS-300` uses
   `attachmentStorage.mode = github-releases` with tag prefix `prefix-`
2. ensures tag `prefix-TS-300` resolves to a conflicting GitHub release titled
   `Manual Release` instead of `Attachments for TS-300`
3. runs the exact ticket command
   `trackstate attachment upload --issue TS-300 --file release-conflict.txt --target hosted --provider github --repository IstiN/trackstate-setup --branch main`
4. verifies the CLI returns the deterministic `REPOSITORY_OPEN_FAILED` conflict
   with the manual-cleanup reason
5. confirms the hosted release assets and `TS-300/attachments.json` state remain
   unchanged after the failed upload

## Install dependencies

```bash
python3 -m pip install pyyaml
```

No other Python packages are required. The test can use a Dart SDK already on
`PATH`, `TRACKSTATE_DART_BIN` / `TS38_DART_BIN`, or bootstrap one into the
runtime tool cache automatically.

## Run this test

```bash
python3 testing/tests/TS-503/test_ts_503.py
```

## Required environment / config

- Python 3.12+
- `GH_TOKEN` or `GITHUB_TOKEN` with write access to `IstiN/trackstate-setup`
- Network access to the GitHub API
- Optional: `TRACKSTATE_DART_BIN` / `TS38_DART_BIN` for a specific Dart SDK
- Optional: `TRACKSTATE_TOOL_CACHE` / `TS38_TOOL_CACHE` to override the Dart
  bootstrap cache location

## Expected pass / fail behavior

- **Pass:** the script exits successfully, records the deterministic
  `REPOSITORY_OPEN_FAILED` / release-mismatch output, and confirms the
  conflicting release plus attachment manifest were not mutated.
- **Fail:** the script raises an assertion error and writes the observed
  mismatch, CLI output, and hosted-state details to `outputs/bug_description.md`.
