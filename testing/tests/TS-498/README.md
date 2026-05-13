# TS-498

Verifies the hosted **Project Settings** repository-access area preserves the
approved stacked pattern and storage-aware styling when attachment storage
changes from repository-path to GitHub Releases.

The automation:
1. launches the production hosted Settings screen with repository-path storage
   and partial hosted attachment support
2. confirms the repository-access status band and secondary attachment callout
   render in stacked amber warning styling above the token controls
3. opens **Project Settings > Attachments**, switches the storage mode to
   **GitHub Releases**, enters a valid tag prefix, and saves
4. confirms the same stacked hierarchy updates to the green GitHub Releases
   success styling with the expected user-facing text

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-498/test_ts_498.dart -r expanded
```

## Required environment / config

No external credentials are required. The test uses a hosted widget fixture and
mocked shared preferences.

## Expected passing output

```text
00:00 +0: TS-498 repository access UI keeps stacked layout and storage-specific styling
00:00 +1: All tests passed!
```
