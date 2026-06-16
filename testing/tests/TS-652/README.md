# TS-652

Validates that the production CLI response formatter still renders the primary
success output when it emits a schema validation warning for non-canonical link
metadata such as `{"type":"blocks","direction":"inward"}`.

The automation:
1. runs a Dart probe against the live `lib/cli/trackstate_cli.dart` source
2. passes the non-canonical link payload from the Python test config into the
   probe
3. invokes the production formatter success path through Dart mirrors with that
   `IssueLink(type: "blocks", targetKey: "TS-2", direction: "inward")`
4. captures the real JSON success output, the terminal-style success text, and
   any writes to `stderr`
5. verifies the warning appears on `stderr` without interrupting either visible
   success output

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-652 -p 'test_*.py' -v
```

## Environment

- Python 3.12+
- Dart SDK available on `PATH` or bootstrapped by `PythonDartProbeRuntime`

## Expected result

The formatter should keep the JSON and text success output intact while also
writing a warning to `stderr` explaining that `blocks` must use the canonical
`outward` direction.
