# TS-129

Validates the compliant path for the repository theme-token policy gate by
creating a temporary copy of the repository, adding a Flutter widget that uses
the centralized TrackState theme token
`Theme.of(context).colorScheme.primary`, and running the supported enforcement
command against that probe file.

The automation only passes when the command behaves like a user would expect in
the terminal:
1. `dart run tool/check_theme_tokens.dart <file>` exits successfully for the
   tokenized widget, and
2. the terminal output stays clean and reports that no theme-token policy
   violations were found.

## Install dependencies

No Python packages are required beyond the standard library.

The test needs a Flutter SDK. It will use one of these, in order:
1. `TS115_FLUTTER_BIN`
2. `TRACKSTATE_FLUTTER_BIN`
3. `/tmp/flutter/bin/flutter`
4. `flutter` on `PATH`
5. an automatically bootstrapped Flutter SDK cached under
   `~/.cache/trackstate-test-tools/`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-129 -p 'test_*.py'
```

## Environment variables

- `TS115_FLUTTER_BIN` or `TRACKSTATE_FLUTTER_BIN` (optional): absolute path to
  a preinstalled `flutter` executable.
- `TS115_FLUTTER_VERSION` (optional): Flutter version to bootstrap when a local
  SDK is unavailable. Defaults to `3.35.3`.
- `TS115_TOOL_CACHE` or `TRACKSTATE_TOOL_CACHE` (optional): cache directory for
  the bootstrapped Flutter SDK archive.
- `TS115_KEEP_TEMP_PROJECT=1` (optional): keep the temporary project copy after
  the test finishes for local debugging.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

## Expected behavior

Running `dart run tool/check_theme_tokens.dart <file>` against a Flutter UI
probe that uses `Theme.of(context).colorScheme.primary` should exit with code 0
and print `No theme token policy violations found.` without any warning or
error diagnostics.
