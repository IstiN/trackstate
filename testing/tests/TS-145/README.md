# TS-145

Validates the live production theme-token policy check for the repository UI
directory when the target is passed with dot-relative notation:
`dart run tool/check_theme_tokens.dart ./lib`.

The automation only passes when a user can run that command at the repository
root and observe:
1. a zero exit status,
2. the success message `No theme token policy violations found.`, and
3. no analyzer-style warning output for the production `./lib` path.

## Install dependencies

No Python packages are required beyond the standard library.

The test needs a Flutter SDK. It will use one of these, in order:
1. `TS132_FLUTTER_BIN`
2. `TS115_FLUTTER_BIN`
3. `TRACKSTATE_FLUTTER_BIN`
4. `/tmp/flutter/bin/flutter`
5. `flutter` on `PATH`
6. an automatically bootstrapped Flutter SDK cached under
   `~/.cache/trackstate-test-tools/`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-145 -p 'test_*.py'
```

## Environment variables

- `TS132_FLUTTER_BIN` or `TRACKSTATE_FLUTTER_BIN` (optional): absolute path to a
  preinstalled `flutter` executable.
- `TS132_FLUTTER_VERSION` or `TRACKSTATE_FLUTTER_VERSION` (optional): Flutter
  version to bootstrap when a local SDK is unavailable. Defaults to `3.35.3`.
- `TS132_SUCCESS_MESSAGE` (optional): expected success text. Defaults to
  `No theme token policy violations found.`
- `TS132_TOOL_CACHE` or `TRACKSTATE_TOOL_CACHE` (optional): cache directory for
  the bootstrapped Flutter SDK archive.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
