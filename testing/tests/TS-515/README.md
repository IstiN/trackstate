# TS-515

Verifies that the **Open settings** recovery action in the issue-detail
**Attachments** restriction notice overrides a previously selected
**Project Settings > Statuses** tab and lands the user directly on
**Project Settings > Attachments**.

The automation:
1. launches the production `TrackStateApp` with a hosted connected session whose
   attachment storage mode is `github-releases` and whose hosted permissions do
   not support release-backed attachment writes
2. opens **Project Settings**, explicitly switches to the **Statuses** tab, and
   confirms status-specific UI is visible while attachment configuration is not
3. returns to the seeded issue detail, opens the visible **Attachments** tab,
   and confirms the inline restriction notice and existing attachment row are
   still present
4. activates the inline **Open settings** recovery action
5. verifies the app navigates back to **Project Settings** with the
   **Attachments** sub-tab active and the **Attachment storage mode**
   configuration visible instead of stale **Statuses** content

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-515/test_ts_515.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test stores a mock hosted token in `SharedPreferences` to simulate a
  connected hosted repository session

## Expected result

```text
Pass: after Statuses was the last selected settings tab, the Attachments notice
still opens Project Settings directly on the Attachments sub-tab and shows the
Attachment storage mode configuration instead of stale status-management UI.

Fail: the Statuses precondition cannot be established, the notice is missing, or
Open settings returns to Project Settings while leaving Statuses content active
or omitting the Attachment storage configuration.
```
