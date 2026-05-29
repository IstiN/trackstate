# TS-482

Verifies that **Project Settings > Attachments** defaults missing
`attachmentStorage` to **Repository Path**, blocks invalid **GitHub Releases**
configuration with a visible validation error, and persists the saved
`attachmentStorage` object to `project.json`.

The automation:
1. seeds a Local Git TrackState repository whose `DEMO/project.json` omits the
   `attachmentStorage` key
2. opens the production Settings > **Attachments** tab and verifies the visible
   default state shows **Repository Path**
3. switches to **GitHub Releases**, clears **Release tag prefix**, and confirms
   the visible **Save failed** banner blocks the write
4. enters `dev-attachments-`, saves successfully, and reads `DEMO/project.json`
   back from disk to confirm the persisted `attachmentStorage` object

## Run this test

```bash
flutter test testing/tests/TS-482/test_ts_482.dart -r expanded
```

## Required configuration

No external credentials are required. The test uses the production widget tree
with a seeded Local Git repository fixture inside the widget-test harness.
