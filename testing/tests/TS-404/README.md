# TS-404

Validates the Settings administration workspace keeps the required tabbed
catalog visible and switches the status editor from a right-side drawer-style
surface on wide layouts to a centered modal surface on narrow layouts.

The automation:
1. launches the real local-repository-backed app with a project settings
   catalog containing statuses, workflows, issue types, and fields
2. opens **Settings** and verifies the visible tabs are **Statuses**,
   **Workflows**, **Issue Types**, and **Fields**
3. confirms the emphasized **Save settings** action renders with the
   TrackStateTheme primary/page token colors used by the production surface
4. opens **Edit status To Do** on a wide viewport and verifies the editor is
   shown as a right-aligned side surface with the expected visible fields
5. resizes to a narrow viewport, reopens **Edit status To Do**, and verifies
   the editor is shown as a centered modal with the same visible fields

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-404/test_ts_404.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test creates and disposes its own Local Git repository fixture

## Expected result

```text
Pass: Settings shows the four required tabs, Save settings uses the expected
theme token colors, Edit status opens as a right-side surface on wide layouts,
and reopening it on a narrow layout shows a centered modal surface.

Fail: one or more required tabs are missing, the visible Save settings action
does not use the expected theme colors, or the edit surface does not switch
between the wide and narrow responsive presentations.
```
