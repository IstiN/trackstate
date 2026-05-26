# TS-885

Validates the desktop **Edit issue** side-sheet against the approved golden
baseline.

The automation:
1. launches the seeded issue detail flow through the shared Issue Edit fixture
2. opens the visible **Edit issue** side-sheet for the existing local issue
3. resizes the viewport to the required **1440x900** desktop size before the
   golden comparison
4. verifies the visible labels, actions, and seeded Summary/Description values
5. captures the rendered desktop surface and compares it pixel-for-pixel with
   the ticket baseline at `testing/tests/TS-885/goldens/edit_issue_desktop.png`

## Direct widget test command

```bash
flutter test testing/tests/TS-885/test_ts_885.dart -r expanded
```

## Expected result

```text
Pass: the Edit issue side-sheet remains visible at 1440x900, shows the required
labels and seeded values, and matches the approved golden baseline.

Fail: required Edit issue content is missing, the side-sheet no longer lays out
correctly at 1440x900, or the rendered surface regresses from the approved
golden image at `testing/tests/TS-885/goldens/edit_issue_desktop.png`.
```
