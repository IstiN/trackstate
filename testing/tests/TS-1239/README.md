# TS-1239

Validates the global repository-access surface at the required **1440x960**
desktop viewport with production widget rendering and golden baselines.

The automation:
1. launches the production `TrackStateApp` in the hosted unauthenticated state
2. verifies the disconnected banner text and CTA, then compares the production
   banner surface with the approved golden while the app stays at 1440x960
3. connects with a read-only token through the production dialog
4. verifies the read-only banner text, confirms the long user-facing message
   wraps across multiple lines without framework overflow errors, and compares
   the production banner golden at the same viewport
5. reconnects with writable permissions in the same hosted session, verifies
   the visible `Connected` state removes the global warning banner, opens
   Settings, and compares only the scoped full-access repository-access state
   label golden at the same viewport

## Run this test

```bash
flutter test testing/tests/TS-1239/test_ts_1239.dart --reporter expanded
```

## Update approved goldens

```bash
flutter test testing/tests/TS-1239/test_ts_1239.dart --update-goldens
```

## Expected result

```text
Pass: the repository-access UI renders the approved unauthenticated,
read-only, and full-access desktop states at 1440x960 without RenderFlex
overflow errors, the read-only banner message stays visibly wrapped, and the
connected Settings repository-access state label remains visually stable.

Fail: the banner text/CTA is missing, the read-only message does not wrap
cleanly, a framework overflow occurs, the same-session reconnect does not
reach `Connected`, the full-access state still shows the warning banner, or
any approved golden no longer matches.
```
