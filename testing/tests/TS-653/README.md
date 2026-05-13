# TS-653

Validates that the production CLI response formatter does **not** surface a
schema validation warning when it receives canonical link metadata such as
`{"type":"blocks","direction":"outward"}`.

The automation:
1. runs a Dart probe against the live `lib/cli/trackstate_cli.dart` source
2. invokes the private formatter helpers through Dart mirrors with a manual
   `IssueLink(type: "blocks", targetKey: "TS-2", direction: "outward")`
3. captures the formatted JSON payload, the terminal-style success text, and any
   writes to `stderr`
4. verifies the canonical payload is visible to the user and that `stderr`
   stays empty so the formatter does not emit a false positive warning

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-653 -p 'test_*.py' -v
```

## Environment

- Python 3.12+
- Dart SDK available on `PATH` or bootstrapped by `PythonDartProbeRuntime`

## Expected result

The formatter should preserve the visible canonical payload and leave `stderr`
empty because `blocks` already uses the canonical `outward` direction.
