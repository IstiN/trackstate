# TS-705

Validates the first-launch onboarding accessibility flow on the production
TrackState Flutter screen, including visible copy, semantics labels, keyboard
focus order, rendered contrast, and the live theme-token policy command for
`lib/ui/features/tracker/views/trackstate_app.dart`.

The automation only passes when a user can open onboarding with no saved
workspace profiles and observe:
1. the expected onboarding copy for both local-folder and hosted-repository
   modes,
2. descriptive non-empty semantics labels for the segmented choices, text
   inputs, and Open action,
3. logical keyboard traversal with `Tab` and `Shift+Tab`,
4. AA-compliant contrast on the rendered onboarding text surfaces, and
5. `dart run tool/check_theme_tokens.dart lib/ui/features/tracker/views/trackstate_app.dart`
   succeeding without warnings.

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
flutter test testing/tests/TS-705/test_ts_705.dart --reporter expanded
```

## Expected behavior

The test should exercise the real onboarding UI and either:
1. pass when onboarding semantics, focus order, contrast, and theme-token policy
   all match the ticket expectation, or
2. fail with recorded evidence that reflects the real production-visible defect.
