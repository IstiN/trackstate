# TS-516

Verifies that the production **Attachments** tab hides the release-storage
restriction notice when the hosted session supports browser uploads for
**GitHub Releases** attachment storage.

The automation:
1. launches the production `TrackStateApp` with a remembered hosted token and a
   reactive repository fixture configured for `attachmentStorage.mode =
   github-releases`
2. opens the seeded `TRACK-12` issue and switches to the **Attachments** tab
3. verifies the release-storage restriction notice and `Open settings` recovery
   action stay hidden
4. confirms the standard upload controls remain visible at the top of the tab
5. verifies the existing release-backed attachment row stays visible with its
   download action

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-516/test_ts_516.dart --reporter expanded
```

## Required environment / config

No external credentials are required. The test uses the production widget tree
with hosted repository fixtures and mocked shared preferences inside the widget
test harness.

## Expected result

```text
Pass: the Attachments tab keeps the standard upload picker visible, preserves
the existing attachment row and download action, and does not render any
release-storage restriction notice or `Open settings` recovery action.

Fail: the restriction notice or recovery action appears, the upload controls are
missing, or the existing attachment row disappears from the Attachments tab.
```
