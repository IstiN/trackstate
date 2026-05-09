# TS-131

Validates the deployed pull-request CI gate for non-tokenized Flutter colors by
creating a disposable branch and Pull Request in `IstiN/trackstate`, waiting for
the exact PR workflow run, and confirming that `Enforce theme tokens` fails in a
merge-blocking way.

The automation also reuses the repository's real
`dart run tool/check_theme_tokens.dart` gate locally and requires the hardcoded
color probe to fail with a non-zero exit status while still showing a
contributor-visible diagnostic.

## Install dependencies

No extra Python packages are required beyond the repository dependencies already
used by the existing `testing/` suite.

## Run this test

```bash
TS131_RESULT_PATH=outputs/ts131_run.json \
python3 -m unittest discover -s testing/tests/TS-131 -p 'test_*.py' -v
```

## Required environment

- `gh` must be installed and authenticated with permission to push branches and
  create Pull Requests in `IstiN/trackstate`.
- Network access to GitHub REST APIs is required.
- A Flutter SDK is required for the reused hardcoded-hex probe. The runtime uses
  the same resolution order documented in `testing/tests/TS-115/README.md`.

## Expected passing output

```text
test_pull_request_ci_gate_blocks_non_tokenized_colors ... ok
```
