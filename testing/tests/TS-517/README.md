# TS-517

Verifies that the **Attachments** tab keeps the release-storage restriction
notice positioned at the top of the tab content while a long attachment list
remains scrollable end to end.

The automation:
1. launches the production `TrackStateApp` with a hosted connected session whose
   attachment storage mode is `github-releases`, whose hosted permissions do not
   support release-backed uploads, and whose issue contains 12 existing
   attachments
2. opens the seeded issue detail and switches to the visible `Attachments` tab
3. verifies the inline restriction notice renders its user-facing title,
   description, and `Open settings` action above the attachment rows
4. verifies the issue-detail surface becomes vertically scrollable, scrolls to
   the last attachment row, and confirms the bottom row becomes visible
5. scrolls back to the top and verifies the notice is still inline above the
   first visible attachment row

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-517/test_ts_517.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test stores a mock hosted token in `SharedPreferences` to simulate a
  connected hosted repository session

## Expected result

```text
Pass: the Attachments notice stays inline above the seeded attachment list, the
issue-detail view scrolls to the bottom attachment row without hiding rows
behind the notice, and scrolling back restores the notice above the list.

Fail: the notice is missing or detached from the Attachments surface, the list
does not become scrollable with 10+ attachments, the bottom attachment row never
becomes visible, or scrolling back no longer restores the notice above the
attachment rows.
```
