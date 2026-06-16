# TS-1260

Validates the first-launch local onboarding flow field-label contrast on the
production TrackState Flutter screen.

The automation only passes when a user can open onboarding, remain on the
default **Local folder** flow, see the visible `Repository Path`, `Branch`, and
`Enter the local Git folder path.` copy, and observe those exact rendered text
elements at AA-compliant contrast on the white onboarding surface.

## Run this test

```bash
flutter test testing/tests/TS-1260/test_ts_1260.dart --reporter expanded
```

## Expected behavior

The test should exercise the real onboarding UI and pass only when the live
rendered text uses the deployed muted token outcome `#5B5A52` on `#FFFFFF`,
producing `6.93:1` contrast for the three ticketed elements.
