# TS-111

Validates that the dirty local save error banner in Local Git mode exposes a
functional dismiss control and disappears after the user clicks it.

The automation:
1. creates a temporary local Git repository fixture
2. dirties `DEMO/DEMO-1/main.md` outside TrackState
3. launches the real `TrackStateApp` in Local Git mode
4. edits the same issue and clicks `Save`
5. verifies the visible `Save failed:` banner includes `commit`, `stash`, and
   `clean` guidance
6. dismisses that banner through the user-visible control
7. verifies the banner is removed and the user can continue in `Search`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-111/test_ts_111.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: the dirty-save failure banner exposes a visible dismiss action, disappears
after the user clicks it, and the app remains usable afterward.

Fail: no dismiss control is rendered, tapping it does not remove the banner, or
the app remains blocked by the message.
```
