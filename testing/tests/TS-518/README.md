# TS-518

Verifies that keyboard focus moves directly from the inline **Open settings**
action in the **Attachments** restriction notice to the first attachment download
action when hosted GitHub Releases uploads are unavailable.

The automation:
1. launches the production Flutter app with a remembered hosted token and a
   repository fixture configured for `attachmentStorage.mode = github-releases`
2. opens the seeded `TRACK-12` issue and switches to the **Attachments** tab
3. verifies the visible warning notice and the existing attachment row render in
   the issue detail
4. tabs forward until **Open settings** is focused
5. presses `Tab` one more time and verifies the next focused control is
   **Download sync-sequence.svg**

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-518/test_ts_518.dart --reporter expanded
```

## Required environment / config

No external credentials are required. The test uses the production widget tree
with hosted repository fixtures and mocked shared preferences inside the widget
test harness.
