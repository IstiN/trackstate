# TS-157

Validates the deployed theme-token enforcement command from a terminal user's
perspective when the target directory contains a nested violation.

The automation creates a temporary repository copy, runs
`dart run tool/check_theme_tokens.dart lib/` once as a clean baseline, then
adds `lib/nest_test/violation.dart` with the hardcoded literal
`Color(0xFF112233)` and reruns the same parent-directory command.

The test only passes when the clean run succeeds first and the second run
fails with analyzer-style diagnostics that point to the nested file and its
numeric line/column location.

## Install dependencies

No Python packages are required beyond the standard library.

The test needs a Flutter SDK. It will use one of these, in order:
1. `TS157_FLUTTER_BIN`
2. `TS132_FLUTTER_BIN`
3. `TS115_FLUTTER_BIN`
4. `TRACKSTATE_FLUTTER_BIN`
5. `/tmp/flutter/bin/flutter`
6. `flutter` on `PATH`
7. an automatically bootstrapped Flutter SDK cached under
   `~/.cache/trackstate-test-tools/`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-157 -p 'test_*.py'
```

## Environment variables

- `TS157_FLUTTER_BIN` or `TRACKSTATE_FLUTTER_BIN` (optional): absolute path to a
  preinstalled `flutter` executable.
- `TS157_FLUTTER_VERSION` or `TRACKSTATE_FLUTTER_VERSION` (optional): Flutter
  version to bootstrap when a local SDK is unavailable. Defaults to `3.35.3`.
- `TS157_TARGET_PATH` (optional): target passed to the policy command. Defaults
  to `lib/`.
- `TS157_PROBE_PATH` (optional): nested Dart file created in the temporary copy.
  Defaults to `lib/nest_test/violation.dart`.
- `TS157_KEEP_TEMP_PROJECT=1` (optional): keep the temporary project copy after
  the test finishes for local debugging.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
