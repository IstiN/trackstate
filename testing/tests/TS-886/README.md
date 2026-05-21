# TS-886

Validates the desktop **Settings > Admin** surface against the approved golden
baseline.

The automation:
1. launches the same desktop Settings administration surface used by the
   approved production golden baseline
2. opens **Settings** and verifies the visible **Project Settings** and
   **Project settings administration** headings
3. confirms the visible admin tabs are **Statuses**, **Workflows**,
   **Issue Types**, and **Fields**
4. checks the visible primary actions a user relies on before the visual
   comparison
5. captures the rendered desktop viewport and compares it pixel-for-pixel with
   the approved baseline stored in `test/goldens/settings_admin_desktop.png`

## Run this automation

```bash
python3 testing/tests/TS-886/run_ts_886.py
```

## Direct widget test command

```bash
flutter test testing/tests/TS-886/test_ts_886.dart -r expanded
```

## Expected result

```text
Pass: the Settings admin desktop surface shows the required headings and tabs,
the seeded admin content is visible on each tab, and the rendered viewport
matches the approved golden baseline.

Fail: visible Settings admin content is missing or the desktop surface regresses
from the approved golden image.
```
