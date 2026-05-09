# TS-143

Validates the live production theme-token policy check for the repository UI
directory when the target is passed without a trailing slash:
`dart run tool/check_theme_tokens.dart lib`.

The automation only passes when a user can run that command at the repository
root and observe:
1. a zero exit status,
2. the success message `No theme token policy violations found.`,
3. no analyzer-style warning output for the normalized `lib` path, and
4. no `Theme token policy target does not exist` error for the normalized
   directory target.

## Install dependencies

No Python packages are required beyond the standard library.

The test needs a Flutter SDK. It will use one of these, in order:
1. `TS143_FLUTTER_BIN`
2. `TS132_FLUTTER_BIN`
3. `TS115_FLUTTER_BIN`
4. `TRACKSTATE_FLUTTER_BIN`
5. `/tmp/flutter/bin/flutter`
6. `flutter` on `PATH`
7. an automatically bootstrapped Flutter SDK cached under
   `~/.cache/trackstate-test-tools/`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-143 -p 'test_*.py'
```

## Environment variables

- `TS143_FLUTTER_BIN`, `TS132_FLUTTER_BIN`, or `TRACKSTATE_FLUTTER_BIN`
  (optional): absolute path to a preinstalled `flutter` executable.
- `TS143_FLUTTER_VERSION`, `TS132_FLUTTER_VERSION`, or
  `TRACKSTATE_FLUTTER_VERSION` (optional): Flutter version to bootstrap when a
  local SDK is unavailable. Defaults to `3.35.3`.
- `TS143_TOOL_CACHE`, `TS132_TOOL_CACHE`, or `TRACKSTATE_TOOL_CACHE`
  (optional): cache directory for the bootstrapped Flutter SDK archive.
- `TS143_TARGET_PATH` (optional): target passed to the policy command. Defaults
  to `lib`.
- `TS143_SUCCESS_MESSAGE` (optional): expected success text. Defaults to
  `No theme token policy violations found.`

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
