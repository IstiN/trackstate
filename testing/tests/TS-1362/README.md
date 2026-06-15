# TS-1362 test automation

## Objective

Verify that the compiled native CLI binary maintains full functional parity with the Dart VM entrypoint, specifically regarding JSON output shape and authentication precedence.

## Ticket command mapping

The ticket references `trackstate get-ticket TRACK-1`, which is not a supported CLI command. The canonical equivalent exercised by this test is:

```bash
trackstate read ticket --key TRACK-1 --path /repo --output json
```

The ticket also references `GITHUB_TOKEN` for environment-token precedence. The current CLI implementation uses `TRACKSTATE_TOKEN` as the hosted authentication environment variable, so the test verifies precedence using `TRACKSTATE_TOKEN`.

## What is automated

1. Compile `bin/trackstate.dart` to a temporary standalone executable using `dart compile exe`.
2. Seed a disposable local Git repository with a minimal TrackState project containing `TRACK-1`.
3. Run `trackstate read ticket --key TRACK-1` against both the compiled binary and `dart bin/trackstate.dart`.
4. Parse both outputs and compare the JSON payloads for structural and value equality.
5. Run `trackstate session --target hosted --repository IstiN/trackstate` with `TRACKSTATE_TOKEN` set to an invalid value against both entrypoints.
6. Compare the resulting `AUTHENTICATION_FAILED` JSON envelopes to confirm the environment-token auth path is preserved in the compiled binary.

## Run

```bash
python testing/tests/TS-1362/test_ts_1362.py
```

## Requirements

- Dart SDK available on PATH or via `TRACKSTATE_DART_BIN`.
- Git available on PATH for seeding the disposable local repository.
- Network access to GitHub for the hosted session negative-path check.
