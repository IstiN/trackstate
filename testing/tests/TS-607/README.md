# TS-607

Validates that **Project Settings > Attachments** keeps keyboard focus inside the
local GitHub Releases workflow until the action buttons are exhausted.

The automation:
1. seeds the existing Attachments settings Local Git fixture
2. opens **Project Settings > Attachments** in the production settings surface
3. switches the storage mode to **GitHub Releases** and verifies the visible
   **Release tag prefix** field
4. tabs from **Attachment storage mode** through **Release tag prefix**,
   **Reset**, and **Save settings**
5. verifies that only the next Tab after **Save settings** reaches a global
   navigation control

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-607/test_ts_607.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture
