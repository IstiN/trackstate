# TS-271

Verifies the hosted CLI credential precedence contract against the live
implementation.

The test proves the precedence in two observable steps:

1. run the hosted session command with a valid token injected through
   `TRACKSTATE_TOKEN` and verify the JSON envelope reports `"authSource": "env"`
2. rerun the same hosted session command with the same environment token plus an
   explicit invalid `--token DIFFERENT_INVALID_TOKEN` override and verify the CLI
   returns `AUTHENTICATION_FAILED` with exit code `3`

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-271 -p 'test_*.py'
```

## Environment

The automation accepts a valid hosted token from this precedence for the test
setup itself:

1. `TS271_VALID_TRACKSTATE_TOKEN`
2. `TRACKSTATE_TOKEN`
3. `gh auth token`

Optional overrides:

- `TS271_REPOSITORY` (default: `IstiN/trackstate`)
- `TS271_PROVIDER` (default: `github`)
- `TS271_INVALID_TOKEN` (default: `DIFFERENT_INVALID_TOKEN`)
