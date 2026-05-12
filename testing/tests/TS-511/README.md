# TS-511

Verifies that the **Attachments** tab keeps the release-storage restriction
notice inline at the point of use and exposes the recovery route into
**Project Settings > Attachments** when hosted GitHub Releases uploads are not
available.

The automation:
1. launches the production `TrackStateApp` with a hosted connected session whose
   attachment storage mode is `github-releases` and whose hosted permissions do
   not support release-backed attachment writes
2. opens the seeded issue detail and switches to the visible `Attachments` tab
3. verifies the release-storage restriction notice stays inline inside the
   Attachments surface, renders its user-facing title/message/action, and keeps
   the existing attachment row visible below it
4. activates the inline `Open settings` recovery action
5. verifies the app navigates directly to **Project Settings > Attachments**

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-511/test_ts_511.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test stores a mock hosted token in `SharedPreferences` to simulate a
  connected hosted repository session

## Expected result

```text
Pass: the Attachments notice renders inline below the collaboration tabs, the
existing attachment remains visible underneath it, and `Open settings` opens
Project Settings directly on the Attachments tab.

Fail: the notice is missing or detached from the Attachments surface, the
existing attachment disappears, the recovery action is absent, or `Open
settings` opens Project Settings without landing on the Attachments tab.
```
