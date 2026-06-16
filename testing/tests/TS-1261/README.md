# TS-1261

Validates that the production `SettingsTextField` wrapper keeps label and helper
text styling on the shared muted theme token instead of hardcoded low-contrast
colors.

The automation only passes when the current `main` branch:
1. keeps `_SettingsTextField` wired to `colors.muted` for default label and
   helper text styling in `lib/ui/features/tracker/views/trackstate_app.dart`,
2. renders the first-launch onboarding `Repository Path` label, `Enter the
   local Git folder path.` helper text, and `Branch` label with
   `TrackStateColors.light.muted` (`#5B5A52`) on the white field surface, and
3. passes `dart tool/check_theme_tokens.dart lib/ui/features/tracker/views/trackstate_app.dart`.

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-1261/test_ts_1261.dart --reporter expanded
```

## Expected behavior

The test should prove both the source-level contract and the production-visible
rendering for `SettingsTextField`, then write the required output artifacts
under `outputs/`.
