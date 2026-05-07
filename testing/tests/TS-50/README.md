TS-50 validates that the Settings screen keeps the selected `Connected` provider status readable when color-only cues are removed.

- Reuses the shared Settings screen robot and hosted-provider fixture state.
- Wraps the app in grayscale and protanopia color filters to simulate color-vision-deficiency viewing conditions.
- Verifies the post-filter rendered Settings view with golden baselines so the `Connected` state is proven from actual pixels, not only the widget or semantics tree.

Install dependencies with:

`flutter pub get`

Run with:

`flutter test testing/tests/TS-50/ts50_connected_status_color_filter_test.dart`

Required environment/config:

- No extra environment variables are required.

Expected passing output:

- `All tests passed!`
