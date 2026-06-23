# TS-1438

Verifies the Project Settings Connect GitHub button semantics expose a unique,
tappable button node after the TS-1418 fix.

## Run this test

```bash
flutter test testing/tests/TS-1438/test_ts_1438.dart
```

## Required environment and config

- Flutter SDK available on PATH
- The production `SecondaryButton` widget in `lib/ui/features/tracker/views/widgets/action_buttons.dart`

## Scenario notes

The test pumps the production `SecondaryButton` widget with a Connect GitHub
label and inspects the semantics tree. A passing result means there is exactly
one button semantics node, it has the `Connect GitHub` label, it exposes the
tap action, and a tap on that semantics node triggers the callback.