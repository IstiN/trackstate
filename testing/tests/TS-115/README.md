# TS-115

Validates the prevention mechanism for hardcoded UI hex colors by creating a
temporary copy of the repository, adding a simple Flutter widget that first uses
a theme token (`Theme.of(context).colorScheme.primary`) and then replacing that
token with a hardcoded hex color (`Color(0xFFFAF8F4)`).

The automation only passes when the repository theme-token policy gate behaves
like a user would expect from the terminal:
1. the tokenized widget passes cleanly, and
2. the hardcoded hex variant produces an analyzer-style diagnostic that clearly
   points at the probe file instead of printing `No issues found!`

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
python3 -m unittest discover -s testing/tests/TS-115 -p 'test_*.py'
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
