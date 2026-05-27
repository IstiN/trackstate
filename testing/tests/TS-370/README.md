# TS-370

Verifies the global hosted repository-access banner stays visible across the
main issue flows, reflects the current access mode, and routes users to the
canonical recovery surface.

The automation:
1. launches the production `TrackStateApp` in a hosted unauthenticated state
2. verifies the disconnected banner and `Connect GitHub` CTA across Dashboard,
   Board, JQL Search, Hierarchy, and issue detail
3. opens the production PAT recovery dialog, enters a read-only token, and
   submits it through the component layer
4. expects the app to transition to the `Read-only` banner state, but currently
   records the real production crash when PAT submission disposes a controller
   too early
5. if the read-only state is ever reached, verifies the recovery CTA routes to
   the canonical auth/settings recovery surface

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-370/test_ts_370.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the hosted reactive repository fixture and starts without a
  stored token in `SharedPreferences`

## Expected result

```text
Pass: the global banner stays visible across the covered flows, updates from
"Connect GitHub" to "Read-only" after submitting the read-only PAT, and the
recovery CTA opens the canonical recovery surface.

Fail: the banner disappears on a covered flow, the recovery CTA is missing,
submitting the PAT crashes before the read-only state is visible, or the
recovery CTA does not route to auth/settings.
```
