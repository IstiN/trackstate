# TS-1140

Verifies that the shared mutation feedback component exposes `liveRegion`
semantics so screen readers announce visible error feedback automatically.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped repository fixture
2. opens `Board` and drags `TRACK-41` from `To Do` to `In Progress`
3. forces the production move flow to fail with a validation error
4. verifies the exact failure text is visible to the user
5. locates the `Semantics` widget wrapping that message
6. verifies the widget-level `liveRegion` property is enabled
7. verifies the semantics tree exposes the same message as a live-region alert

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-1140/test_ts_1140.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the mutation failure message is visible, wrapped in a Semantics widget
with liveRegion enabled, and exposed to the semantics tree as an announced
alert for screen readers.

Fail: the visible mutation failure text is missing, the Semantics widget does
not carry the exact message label, or liveRegion is not enabled on the widget
or semantics node.
```
