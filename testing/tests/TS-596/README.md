# TS-596 test automation

Verifies that `bin/trackstate.dart` compiles to a standalone executable with
`dart compile exe` and does not fail with the historical `dart:ui` platform
availability error.

The automation:
1. starts in the repository root
2. runs the exact ticket compile command against `bin/trackstate.dart`
3. validates the generated `bin/trackstate_cli` executable
4. removes `bin/trackstate_cli` after verification so the checkout stays clean

## Run this test

```bash
python testing/tests/TS-596/test_ts_596.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- Optional: set `TRACKSTATE_TS596_SOURCE_ROOT` to a different TrackState checkout
  when the production compile fix must be validated from another worktree

## Expected pass / fail behavior

- **Pass:** the standalone compile exits with code `0`, does not surface
  `dart:ui` platform errors, and produces an executable binary.
- **Fail:** the compile exits non-zero, the output mentions `dart:ui`, or the
  target executable is not created.
