# TS-1003

Verifies the production `SyncPill` accessibility regression fix by rendering the
top-bar workspace sync pill in the `Attention needed` state and asserting its
semantics label preserves the required `Sync error` context.

The automation:
1. launches the production TrackState Flutter app in the supported widget-test
   runtime at the default desktop viewport of 1440x900
2. reuses the existing hosted read-only sync-error fixture so the top-bar sync
   pill reaches the visible `Attention needed` state
3. reads the semantics node for the rendered sync pill and verifies the label
   starts with `Sync error` and still includes `attention needed`
4. taps the pill like a user and confirms Settings opens with the visible
   Workspace sync error content in context

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-1003/test_ts_1003.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
