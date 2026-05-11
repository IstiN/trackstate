# TS-402

Validates the production-visible **Edit issue** surface for a Local Git issue
with keyboard and screen-reader accessibility checks.

The automation:
1. opens the real edit surface for `DEMO-1`
2. verifies the visible edit controls rendered across the full form
3. checks non-empty semantics labels and logical `Tab` / screen-reader order for
   `Status`, `Summary`, `Description`, `Priority`, `Assignee`, `Labels`,
   `Components`, `Fix versions`, `Epic`, `Save`, and `Cancel`
4. clears `Summary`, submits the form, and requires either focus to return to
   `Summary` or semantics-based evidence that the validation error was exposed
5. measures the empty `Summary` placeholder contrast against the WCAG AA
   placeholder threshold

## Run this test

```bash
flutter test testing/tests/TS-402/test_ts_402.dart
```

## Expected result

```text
Pass: the Edit issue surface keeps full-form keyboard order, exposes meaningful
semantics for every visible interactive control, announces or focuses the
summary-required validation state accessibly, and keeps the empty Summary
placeholder at or above 3.0:1 contrast.

Fail: a visible edit control is missing, falls out of logical traversal order,
lacks meaningful semantics, exposes only visual validation feedback, or renders
the empty Summary placeholder below the required contrast threshold.
```
