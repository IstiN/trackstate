# TS-235

Validates that the shared `Create issue` control remains accessibility-labeled
in Local Git mode across Dashboard, Board, JQL Search, and Hierarchy.

The automation:
1. creates a temporary local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. visits Dashboard, Board, JQL Search, and Hierarchy in order
4. verifies the shared top bar visibly renders `Create issue` in each section
5. verifies that same top-bar control exposes the `Create issue` semantics label
6. fails with section-specific top-bar text and semantics snapshots when the
   visible control is missing or loses its accessibility label

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-235/test_ts_235.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit hosted-toolcache path
  shown above
- No extra environment variables are required

## Expected result

```text
Pass: each specified Local Git section keeps the shared top-bar Create issue
control visible and that same control exposes the Create issue semantics label.

Fail: one or more sections do not render the shared top-bar Create issue
control, or the visible top-bar control is missing the Create issue semantics
label required for accessibility tools.
```
