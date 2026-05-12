# TS-449

Validates that the real TrackState app shell renders immediately after the
initial snapshot loads, stays responsive at compact widths, and keeps
navigation interactive while the first background search hydration is still
loading.

The automation:
1. launches the local-repository-backed app with a ticket-specific delayed
   initial `searchIssuePage()` wrapper
2. verifies the desktop shell shows the visible branding, sidebar navigation,
   top-bar controls, and loading state instead of a centered spinner
3. resizes to a compact/mobile viewport and confirms the shell still shows the
   visible branded top bar plus compact navigation while loading remains active
4. taps **Board** during the loading window and verifies the selected section
   changes before hydration completes
5. waits for hydration to finish and confirms the selected Board view keeps its
   visible issue content

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-449/test_ts_449.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture

## Expected result

```text
Pass: the app shell renders immediately after snapshot load without falling back
to a centered spinner, the compact shell remains branded and interactive while
loading banners are visible, and the user can switch to Board before hydration
finishes.

Fail: the shell does not render until hydration completes, required branded or
navigation text is missing during loading, compact navigation is not interactive,
or the selected section does not remain usable after hydration finishes.
```
