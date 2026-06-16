# TS-383

## Run this test

```bash
python3 testing/tests/TS-383/test_ts_383.py
```

## Required configuration

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Dart SDK on `PATH` or `TRACKSTATE_DART_BIN`

## Notes

- The automation completes the hosted ticket command by adding the required `--repository owner/name` option from the live setup configuration.
- It seeds and restores a temporary `TS-22` issue inside the hosted `DEMO` project index so the live GitHub target can be exercised end to end.
