# TS-483

Validates that **Project Settings > Attachments** is a dedicated, accessible
workspace with the expected storage-mode controls.

The automation:
1. seeds a Local Git repository fixture with repository-path attachment storage
2. opens the production Settings screen and verifies **Attachments** appears as a
   dedicated tab alongside the existing settings tabs
3. switches the storage selector between **Repository Path** and
   **GitHub Releases** and verifies **Release tag prefix** appears only for the
   GitHub Releases mode
4. verifies the visible labels, helper copy, semantics labels, keyboard order,
   and button interaction-state styling meet the accessibility expectations

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-483/test_ts_483.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture
