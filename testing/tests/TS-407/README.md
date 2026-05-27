# TS-407

Validates the **Settings > Issue Types** administration flow for editing issue
type hierarchy and choosing icons from the supported TrackState glyph set.

The automation:
1. launches the real local-Git settings administration surface
2. edits the existing **Story** issue type and changes **Hierarchy level** from
   `0` to `1`
3. saves project settings and verifies the updated hierarchy is persisted to
   `config/issue-types.json`
4. reopens **Story** and checks that the **Icon** control exposes an icon picker
   instead of a raw text field or arbitrary upload path

## Run this test

```bash
flutter test testing/tests/TS-407/test_ts_407.dart -r expanded
```

## Expected result

```text
Pass: The Story issue type can be updated to hierarchy level 1, the change is
saved, and the icon control opens a supported TrackState glyph picker without
any arbitrary image upload option.

Fail: The hierarchy level cannot be edited/saved, or the icon control still
renders as a free-form text/upload surface instead of a constrained glyph picker.
```
