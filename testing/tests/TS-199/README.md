# TS-199

Validates that closing the Local Git `Create issue` form intentionally clears
the persisted draft data before the next create attempt.

The automation:
1. creates a temporary Local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Dashboard` and verifies the visible dashboard subtitle
4. opens the top-bar `Create issue` flow and enters
   `Temporary Draft Data` into `Summary`
5. dismisses the overlay with the visible `Cancel` action
6. reopens `Create issue` from the top bar and verifies the new `Summary` field
   is visibly empty while the rest of the form remains available

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-199/test_ts_199.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit hosted-toolcache path
  shown above
- No extra environment variables are required

## Expected result

```text
Pass: after opening Create issue from Dashboard, typing Temporary Draft Data,
and cancelling the overlay, reopening Create issue shows an empty Summary field
with the rest of the create form still visible.

Fail: cancelling leaves the overlay open, Create issue cannot be reopened, or
the reopened Summary field still contains the prior draft data.
```
