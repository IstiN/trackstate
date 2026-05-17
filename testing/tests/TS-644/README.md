# TS-644

Validates that the production CLI response formatter surfaces a validation
warning when it receives non-canonical link metadata such as
`{"type":"blocks","direction":"inward"}`.

The automation:
1. runs a Dart probe against the live `lib/cli/trackstate_cli.dart` source
2. invokes the private formatter helpers through Dart mirrors with a manual
   `IssueLink(type: "blocks", targetKey: "TS-2", direction: "inward")`
3. captures the formatted JSON payload, the terminal-style success text, and any
   writes to `stderr`
4. verifies the invalid payload is visible to the user and that the formatter
   also emits a schema-validation warning describing the mismatch

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-644 -p 'test_*.py' -v
```

## Environment

- Python 3.12+
- Dart SDK available on `PATH` or bootstrapped by `PythonDartProbeRuntime`

## Expected result

The formatter should preserve the visible payload for diagnosis and write a
warning to `stderr` explaining that `blocks` must use the canonical `outward`
direction.
