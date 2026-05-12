# TS-512

Verifies that the production **Attachments** tab keeps its storage restriction
notice accessible when hosted uploads are blocked for **GitHub Releases**
storage.

The automation:
1. launches the production Flutter app with a remembered hosted token and a
   reactive repository fixture configured for `attachmentStorage.mode =
   github-releases`
2. opens the seeded `TRACK-12` issue and switches to the **Attachments** tab
3. checks that the visible warning notice renders the expected title, message,
   and **Open settings** recovery action
4. verifies the notice and recovery button expose meaningful semantics labels
   and that keyboard Tab traversal reaches **Open settings** before the
   attachment download action
5. measures the rendered warning-callout colors and text contrast against the
   TrackState accent token

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-512/test_ts_512.dart -r expanded
```

## Required environment / config

No external credentials are required. The test uses the production widget tree
with hosted repository fixtures and mocked shared preferences inside the widget
test harness.
