# TS-1236

Validates the production-visible **Comments** tab empty comment composer placeholder.

The automation:
1. opens seeded issue `TRACK-12` in the issue detail view
2. switches to the **Comments** tab
3. verifies the visible comment composer actions are rendered for the user
4. requires the empty composer to expose the exact placeholder text `Add a comment...`
5. confirms the placeholder is actually painted in the input before any text is entered

## Run this test

```bash
flutter test testing/tests/TS-1236/test_ts_1236.dart --reporter expanded
```

## Expected result

```text
Pass: the empty Comments composer shows the exact placeholder text
"Add a comment..." inside the input field before the user types.

Fail: the placeholder is missing, the text differs from "Add a comment...",
or the placeholder is not visibly rendered in the empty input field.
```
