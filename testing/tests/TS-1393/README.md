# TS-1393 — CLI Assistant Subcommand

Verifies namespace discovery and session-less invocation of the TrackState CLI assistant subcommand.

## Run this test

```bash
python -m unittest testing.tests.TS-1393.test_ts_1393 -v
```

## What is tested

- `trackstate assistant --help` documents the GitHub and Claude assistants and the separate command namespace.
- `trackstate assistant github` returns a JSON envelope containing the GitHub skill manifest.
- `trackstate assistant claude` returns a JSON envelope containing the Claude skill manifest.
- `trackstate assistant unknown` fails with a validation error and non-zero exit code.
