# TS-182

Validates that the centralized Local Git `Create issue` overlay remains open
and preserves the typed `Summary` value while the user navigates from
`Dashboard` to `Board`.

The automation:
1. creates a temporary Local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Dashboard` and confirms the visible dashboard subtitle
4. opens the top-bar `Create issue` flow
5. enters `Refactor Persistence Verification` into `Summary` and verifies the
   visible field value
6. clicks `Board` in the sidebar while the create overlay remains open
7. checks that the `Board` background becomes visible and the create overlay
   still exposes the same `Summary`, `Description`, `Save`, and `Cancel`
   controls

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-182/test_ts_182.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit hosted-toolcache path
  shown above
- No extra environment variables are required

## Expected result

```text
Pass: after opening Create issue from Dashboard, clicking Board keeps the
overlay open, switches the background view to Board, and preserves the typed
Summary value `Refactor Persistence Verification`.

Current known result on main: fail. The app stays on Dashboard and closes the
Create issue overlay, so the draft Summary is lost. This automation is intended
to reproduce that product-visible defect until the production fix lands.
```
