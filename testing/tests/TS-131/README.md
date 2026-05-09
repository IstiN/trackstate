# TS-131

Validates the real pull-request CI gate for non-tokenized Flutter colors by
creating a disposable branch and Pull Request in `IstiN/trackstate`.

The automation passes only when both of these are true:
1. the live GitHub Actions pull-request workflow for `IstiN/trackstate` visibly
   includes the `Enforce theme tokens` step and a disposable PR causes that
   workflow to fail, and
2. the repository's real `dart run tool/check_theme_tokens.dart` gate rejects a
   hardcoded Flutter color with a non-zero exit code and contributor-visible
   diagnostic output.

## Run this test

```bash
TS131_RESULT_PATH=outputs/ts131_run.json \
python3 -m unittest discover -s testing/tests/TS-131 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to push branches and
  open Pull Requests in `IstiN/trackstate`.
- `GH_TOKEN` or `GITHUB_TOKEN` must be present so git can push the disposable
  branch non-interactively.
- Network access to GitHub REST APIs is required.
- A Flutter SDK is required for the reused hardcoded-hex probe. The runtime uses
  the same resolution order documented in `testing/tests/TS-115/README.md`.

## Expected passing output

```text
test_pull_request_ci_gate_blocks_non_tokenized_colors ... ok
```
