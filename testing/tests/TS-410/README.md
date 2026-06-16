# TS-410

Validates the production-visible **Project settings administration** workspace
for accessibility, semantics, keyboard traversal, and readable admin controls.

The automation:
1. opens `Settings` with an editable project-settings repository fixture
2. verifies the visible admin workspace text and exact semantics labels for the
   `Statuses`, `Workflows`, `Issue Types`, and `Fields` tabs
3. tabs through the `Fields` table using only the keyboard and requires the
   visible `Add field` and `Edit field ...` actions to stay in logical order
4. opens the field editor drawer and verifies the user-facing editor labels and
   control semantics a screen reader depends on
5. opens the status editor, checks the visible `Category` options (`New`,
   `In progress`, `Done`), and measures their rendered contrast against the
   visible menu surface

## Run this test

```bash
flutter test testing/tests/TS-410/test_ts_410.dart -r expanded
```

## Expected result

```text
Pass: the admin workspace exposes meaningful labels for the tabs and editor
controls, keyboard focus can reach the visible field-edit actions in logical
order, and the visible status category options stay at or above WCAG AA 4.5:1
contrast.

Fail: an admin tab or editor control is unlabeled, keyboard Tab traversal skips
or reorders the field-edit actions, the editor drawer omits user-facing labels,
or a visible status category option falls below the required contrast.
```
