# TS-597 test automation

Verifies the repository source for the Flutter-dependency boundary described by
the ticket:
1. `lib/data/` and `lib/domain/` must not import `package:flutter/`.
2. `lib/data/providers/github/github_trackstate_provider.dart` must not import
   Flutter foundation directly and must keep the `foundation_compat.dart`
   `kIsWeb` shim.
3. The provider must show `package:meta` replacement evidence exactly as stated
   in the current ticket.

## Install dependencies

No Python packages are required beyond the standard library.

## Run this test

```bash
python testing/tests/TS-597/test_ts_597.py
```

## Expected result

```text
Pass: the scan finds no `package:flutter/` imports in `lib/data/` or
`lib/domain/`, the GitHub provider uses the compatibility shim instead of
Flutter foundation, and the provider imports `package:meta`.

Fail: any direct Flutter import remains in the data/domain layers, the provider
still imports Flutter foundation, the compatibility shim is missing, or the
provider does not contain the ticket's required `package:meta` import.
```
