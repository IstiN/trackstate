# TS-372

Validates the production-visible blocked state for the issue-detail **Comments**
composer in a hosted read-only session.

The automation:
1. launches the real TrackState app with a connected hosted token that only has
   read access
2. opens an existing issue and switches to the **Comments** tab
3. verifies the composer stays visible while the tab renders the inline
   read-only explanation and recovery CTA
4. confirms the visible `Post comment` action is disabled and the inline CTA
   takes the user to Settings as the recovery path

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-372/test_ts_372.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test stores a mock hosted token in `SharedPreferences` to drive the
  connected read-only provider session

## Expected result

```text
Pass: the Comments tab keeps the comment composer visible, shows inline
read-only guidance with the recovery CTA, disables posting, and routes the user
to Settings from that CTA.

Fail: the composer disappears, the inline read-only explanation or CTA is
missing, posting stays enabled, or the recovery CTA does not take the user to
Settings.
```
