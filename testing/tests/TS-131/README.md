# TS-131

Validates the real pull-request CI gate for non-tokenized Flutter colors by
creating a disposable branch and Pull Request in `IstiN/trackstate`.

The automation only passes when all of these are true:
1. the live GitHub Actions workflow still declares the `pull_request` trigger,
   `Enforce theme tokens` step, and `dart run tool/check_theme_tokens.dart`
   command,
2. a disposable PR containing a hardcoded Flutter color produces a failed
   `pull_request` workflow run where the `Enforce theme tokens` step concludes
   `failure`, and
3. the PR's status checks leave the PR in a blocked state before the test closes
   the PR and deletes the temporary branch.

## Run this test

```bash
TS131_RESULT_PATH=outputs/ts131_run.json \
python3 -m unittest discover -s testing/tests/TS-131 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to create branches,
  open/close pull requests, and read GitHub Actions data for `IstiN/trackstate`.
- Network access to GitHub REST and GraphQL APIs is required.
- A Flutter SDK is required for the reused hardcoded-hex probe. The runtime uses
  the same resolution order documented in `testing/tests/TS-115/README.md`.

## Expected passing output

```text
test_pull_request_ci_gate_blocks_non_tokenized_colors ... ok
```
