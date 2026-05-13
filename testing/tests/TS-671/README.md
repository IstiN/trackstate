# TS-671

Verifies that the compiled `trackstate ticket --help` output visibly documents
the `show` action in the ticket sub-command action list.

The automation:
1. compiles a temporary repository-local `trackstate` executable from this
   checkout
2. runs `trackstate ticket --help` through that compiled entry point
3. verifies the visible `Actions:` section includes `show` with the deployed
   ticket-detail description
4. verifies the help output also includes the
   `trackstate ticket show --target local --key TRACK-1` example
5. writes the required result artifacts to `outputs/`

## Install dependencies

No Python packages are required beyond the standard library and the
repository's existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the compiled CLI harness executes
  through `flutter test`

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-671/test_ts_671.py
```

## Required environment / config

No ticket-specific environment variables are required.

## Expected passing output

```text
TS-671 passed
```
