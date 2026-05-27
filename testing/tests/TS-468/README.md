# TS-468

Verifies that `trackstate read components` exposes localized `displayName`
metadata only when a locale is requested and marks missing translations with a
machine-readable `usedFallback` flag.

The automation:
1. seeds a Local Git TrackState repository with two components and localized
   labels
2. runs `trackstate read components` with no locale and verifies the canonical
   payload stays unchanged
3. runs `trackstate read components --locale fr` and verifies translated
   `displayName` values are returned without fallback
4. runs `trackstate read components --locale de` and verifies the untranslated
   component falls back to the canonical label with `usedFallback: true`
5. checks the terminal-visible JSON fragments a CLI user would see for each
   command

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-468 -p 'test_ts_468.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile the temporary TrackState CLI.
