# TS-603

Reproduces the local CLI attachment-storage validation scenario for an
unsupported `project.json attachmentStorage.mode` value.

The automation:
1. seeds a disposable local TrackState repository with issue `TS-10`
2. sets `TS/project.json` to an unsupported attachment storage mode string
3. runs the real local attachment upload command from the seeded repository
4. checks the terminal-visible JSON output for the invalid-mode reason
5. verifies the machine-readable error contract does not fall back to a generic
   attachment upload repository failure
6. confirms no attachment files or metadata were created

## Run this test

```bash
python3 testing/tests/TS-603/test_ts_603.py
```

## Required configuration

No Python packages are required beyond the standard library and the repository's
existing test dependencies. The repository under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used by the local CLI harness
- the `git` CLI available on `PATH`
