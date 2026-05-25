# TS-393

Validates the production-visible **Comments** tab comment composer accessibility.

The automation:
1. opens the seeded issue detail fixture and switches to the **Comments** tab
2. verifies the visible comment composer and user-facing comment actions are rendered
3. requires the composer to expose a real placeholder hint, not just the field label
4. measures the placeholder contrast against the filled input surface and checks it
   against the WCAG AA 3.0:1 placeholder threshold
5. enters draft text and verifies typed content remains visually distinct from the
   placeholder styling

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-393/test_ts_393.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```

## Expected result

```text
Pass: the Comments tab shows a real placeholder hint in the comment composer,
the placeholder contrast is at or above 3.0:1, and typed comment text uses a
different visual treatment from the placeholder.

Fail: the comment composer has no placeholder hint, the placeholder contrast is
below 3.0:1, or typed text uses the same styling as the placeholder.
```
