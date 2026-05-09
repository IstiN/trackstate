# TS-131

Validates the deployed pull-request CI gate for non-tokenized Flutter colors
without creating or pushing a branch.

The automation passes only when both of these are true:
1. the live GitHub Actions pull-request workflow for `IstiN/trackstate` visibly
   includes and executes the `Enforce theme tokens` step, and
2. the repository's real `dart run tool/check_theme_tokens.dart` gate rejects a
   hardcoded Flutter color in the same way a contributor would observe from the
   terminal.

## Run this test

```bash
TS131_RESULT_PATH=outputs/ts131_run.json \
python3 -m unittest discover -s testing/tests/TS-131 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with access to read workflow metadata
  for `IstiN/trackstate`.
- Network access to GitHub REST APIs is required.
- A Flutter SDK is required for the reused hardcoded-hex probe. The runtime uses
  the same resolution order documented in `testing/tests/TS-115/README.md`.

## Expected passing output

```text
test_pull_request_ci_gate_blocks_non_tokenized_colors ... ok
```
