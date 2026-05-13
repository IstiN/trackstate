# TS-605

Verifies keyboard users can tab through the hosted *Project Settings → Repository access*
token controls without focus skipping the visible remember/connect actions.

The automation:
1. launches the production Flutter Settings screen with a remembered hosted token
2. opens *Project Settings → Repository access* in both fully available and limited
   attachment-upload states
3. focuses the visible *Fine-grained token* field and verifies successive `Tab`
   presses move to *Remember on this browser* and then *Connect token*
4. confirms the controls remain visibly present while the user moves through the flow

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-605/test_ts_605.dart -r expanded
```

## Required environment / config

No external credentials are required. The test uses the in-repo widget harness,
hosted repository fixtures, and mocked shared preferences.

## Expected passing output

```text
00:00 +0: TS-605 Tab navigation from the fine-grained token field reaches Remember and Connect in order
00:00 +1: All tests passed!
```
