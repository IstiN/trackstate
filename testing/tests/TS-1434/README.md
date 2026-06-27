# TS-1434

Regression test for the TS-1412 bug: the Settings Admin Workspace field editor
must render the expected "Type" label and expose it to assistive technologies.

The automation:
1. opens `Settings` with an editable project-settings repository fixture
2. selects the `Fields` tab
3. opens the first field editor
4. verifies the visible "Type" label text is present
5. verifies a semantics label containing "Type" is exposed inside the editor

## Run this test

```bash
flutter test testing/tests/TS-1434/test_ts_1434.dart -r expanded
```

## Expected result

Pass: the field editor shows the "Type" label and the label is reachable by
screen readers.

Fail: the field editor omits the "Type" label or the label is missing from the
semantics tree, reproducing the TS-1412 accessibility failure.
