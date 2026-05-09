# TS-130

Validates the deployed theme-token enforcement command from a user perspective.
The automation creates a temporary repository copy, writes the requested probe file
at `lib/ts115_lint_probe.dart`, and runs
`dart run tool/check_theme_tokens.dart lib/ts115_lint_probe.dart` twice:

1. with `Theme.of(context).colorScheme.primary`, which must pass cleanly; and
2. with `Color(0xFFFAF8F4)`, which must fail with an analyzer-style warning that
   identifies the probe file, offending literal, and numeric line/column.

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
python3 -m unittest discover -s testing/tests/TS-130 -p 'test_*.py'
```

## Environment variables

- `TS115_FLUTTER_BIN` or `TRACKSTATE_FLUTTER_BIN` (optional): absolute path to a
  preinstalled `flutter` executable.
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
