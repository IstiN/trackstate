# TS-396

Validates the deployed shared **Edit issue** surface from multiple user-visible
entry points.

The automation:
1. opens the live hosted tracker and ensures the session is connected
2. opens `DEMO-3` from **Board**, launches **Edit**, and verifies the desktop
   edit surface behaves like a right-side drawer
3. checks the visible **Summary**, **Description**, and **Priority** values are
   preloaded from the selected issue
4. closes the editor, opens the same issue from the **JQL Search** issue detail
   pane, and verifies the same preloaded values again
5. resizes to a compact `390x844` viewport, opens **Edit** again, and verifies
   the surface expands to a near full-width sheet while keeping the same
   preloaded issue data

## Run this test

```bash
python testing/tests/TS-396/test_ts_396.py
```

## Required environment and config

- Playwright dependencies installed
- `GH_TOKEN` or `GITHUB_TOKEN` available for the hosted GitHub session

## Expected result

```text
Pass: The live Edit issue surface opens from the Board-origin and issue-detail
flows with the selected issue's Summary, Description, and Priority already
loaded. Desktop stays docked to the right; compact expands to a near full-width
sheet.

Fail: Any entry point cannot open Edit, the visible fields are not preloaded
with the current issue metadata, or the responsive surface geometry does not
match the expected desktop-vs-compact behavior.
```
