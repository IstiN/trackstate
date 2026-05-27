# TS-496

Verifies that the hosted **Project Settings** repository-access surface keeps the
provider in an attachment-restricted state when generic repository write access
is available but GitHub Releases attachment uploads are not supported in the
browser.

The automation:
1. launches the production Flutter app with a remembered hosted token and a
   reactive repository fixture configured for `attachmentStorage.mode =
   github-releases`
2. keeps repository Contents write access enabled while
   `supportsReleaseAttachmentWrites` is `false`
3. opens **Project Settings** and verifies the repository-access state remains
   **Attachments limited** instead of falling back to **Connected**
4. checks the release-specific warning callouts, semantics labels, and amber
   warning treatment
5. types into the visible **Fine-grained token** field to confirm the hosted
   repository-access form remains interactive

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-496/test_ts_496.dart -r expanded
```

## Required environment / config

No external credentials are required. The widget test uses the production app
shell with hosted repository fixtures and mocked shared preferences inside the
test harness.

## Expected result

```text
Pass: Project Settings stays in the Attachments limited state, shows the
release-upload restriction warnings with amber treatment, and keeps the hosted
token form usable.

Fail: the UI reports Connected, omits the warning callouts, loses the warning
semantics/treatment, or treats generic repository write access as full
attachment upload support.
```
