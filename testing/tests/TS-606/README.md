# TS-606

Validates the keyboard focus order in **Project Settings > Attachments** after
switching **Attachment storage mode** to **GitHub Releases**.

The automation:
1. seeds a Local Git repository fixture with the Attachments settings surface
2. opens **Settings > Attachments** and switches the storage mode to
   **GitHub Releases**
3. uses keyboard Tab navigation to move focus into **Release tag prefix**
4. verifies the next two Tab stops are the visible **Reset** and
   **Save settings** buttons
5. confirms focus does not leak to global navigation such as **Create issue**

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-606/test_ts_606.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture
