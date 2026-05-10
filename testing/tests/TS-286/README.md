# TS-286

Validates that a failed `Move Issue` mutation exposes accessible feedback for
screen readers instead of relying on color alone.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped repository fixture
2. opens `Board` and drags `TRACK-41` from `To Do` to `In Progress`
3. forces the production move flow to fail with a validation error
4. verifies the exact failure text is visible in the UI
5. verifies the same text is exposed as a semantics label
6. verifies the semantics tree marks that failure as a live-region announcement

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-286/test_ts_286.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: a failed move shows visible validation feedback, the failure category is
readable as text, and screen readers can discover the same message as an alert.

Fail: the move failure text is missing, the semantics label does not match the
visible message, or the failure notification is not exposed as an announced
live region.
```
