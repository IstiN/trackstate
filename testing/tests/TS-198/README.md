# TS-198

Validates that the centralized Local Git `Create issue` action behaves like a
singleton when the user triggers it again while the overlay is already open.

The automation:
1. creates a temporary Local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Dashboard` and confirms the visible dashboard subtitle
4. opens the top-bar `Create issue` flow
5. enters `Singleton Pattern Verification` into `Summary` and verifies the
   visible field value
6. clicks the same top-bar `Create issue` control again without closing the
   current overlay
7. checks that exactly one visible `Summary` field remains, the existing draft
   text is preserved, and the full create surface still exposes `Description`,
   `Save`, and `Cancel`

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-198/test_ts_198.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit hosted-toolcache path
  shown above
- No extra environment variables are required

## Expected result

```text
Pass: after opening Create issue from Dashboard, clicking the same top-bar
Create issue action again keeps a single overlay instance open and preserves the
typed Summary value `Singleton Pattern Verification`.
```
