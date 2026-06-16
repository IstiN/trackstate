# TS-268

Verifies that the root TrackState CLI resolves a hosted GitHub target from the
provider-neutral flags in the ticket command:

`trackstate --target hosted --provider github --repository owner/repo --branch main`

The Python test is the CI entrypoint. It runs a Dart probe that imports the live
CLI implementation, injects a fake hosted provider plus a mocked `gh auth token`
result, and inspects the emitted JSON envelope exactly as a CLI user would see
it in the terminal.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-268 -p 'test_*.py' -v
```

## Environment

The shared Dart probe runtime accepts these optional overrides:

- `TRACKSTATE_DART_BIN`: absolute path to a preinstalled `dart` executable
- `TS38_DART_BIN`: legacy alias checked before `TRACKSTATE_DART_BIN`
- `TRACKSTATE_TOOL_CACHE` / `TS38_TOOL_CACHE`: directory used for the cached SDK

## Expected result

The command should succeed and expose a JSON envelope whose visible metadata
still shows:

- `"provider": "github"`
- `"target": { "type": "hosted", "value": "owner/repo" }`
- `"branch": "main"`
